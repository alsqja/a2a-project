import asyncio
import logging
import os
import numpy as np
import faiss  # FAISS 벡터 데이터베이스용
# openai 라이브러리 임포트 방식 및 사용법이 1.0.0 버전 기준으로 변경됨
from openai import AsyncOpenAI  # OpenAI 클라이언트
from dotenv import load_dotenv  # API 키 관리용
from typing import List, Tuple, Dict, Any, Optional

from agents import Agent, Runner  # 기존 Agent, Runner 사용 가정
from asgiref.sync import sync_to_async
from django.db import close_old_connections

# Django 모델 임포트
from chat_agent.models import Company, CompanyFile, Lead, Chat, ChatRoom

# 환경 변수 로드 (예: OPENAI_API_KEY)
load_dotenv()

logger = logging.getLogger(__name__)

# --- OpenAI 및 FAISS 설정 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

# OpenAI 비동기 클라이언트 초기화 (openai >= 1.0.0 방식)
# API 키는 환경변수 OPENAI_API_KEY에서 자동으로 로드되거나, 명시적으로 전달할 수 있습니다.
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

# OpenAI 임베딩 모델 설정
EMBEDDING_MODEL = "text-embedding-3-small"  # 새롭고 비용 효율적인 모델
EMBEDDING_DIM = 1536  # text-embedding-3-small 기본 출력 차원


# --- RAG 컴포넌트 (OpenAI + FAISS) ---

async def get_openai_embedding(text: str, model: str = EMBEDDING_MODEL) -> Optional[np.ndarray]:
    """
    OpenAI API를 사용하여 주어진 텍스트에 대한 임베딩을 생성합니다.
    최신 openai 라이브러리(>=1.0.0)의 비동기 클라이언트를 사용합니다.
    잠재적인 API 오류를 처리합니다.
    """
    text = text.replace("\n", " ")  # OpenAI 권장 사항
    try:
        response = await aclient.embeddings.create(input=[text], model=model)
        embedding_data = response.data[0].embedding  # 필드 접근 방식 변경됨
        return np.array(embedding_data, dtype=np.float32)
    except Exception as e:  # 좀 더 일반적인 예외 처리 (OpenAI 라이브러리 자체 오류 포함)
        logger.error(f"임베딩 생성 중 OpenAI API 오류 발생: {e}")
    return None


class ConversationMemory:
    def __init__(self, summarization_agent: Optional[Agent] = None, top_k: int = 3,
                 faiss_dimension: int = EMBEDDING_DIM):
        self.faiss_dimension = faiss_dimension
        # 코사인 유사도를 위한 IndexFlatIP 사용 (정규화된 벡터 필요)
        # OpenAI 임베딩은 미리 정규화되어 있음.
        self.index = faiss.IndexFlatIP(self.faiss_dimension)
        self.document_store: List[Dict[str, Any]] = []  # 원본 텍스트 및 메타데이터 저장
        self.summarization_agent = summarization_agent  # 요약에 사용될 Agent
        self.top_k = top_k  # 관련 컨텍스트 검색 시 반환할 상위 K개
        self.turn_count = 0  # 대화 턴 수 또는 고유 ID 부여용

    async def _summarize_text(self, text_to_summarize: str) -> str:
        """ (선택적) LLM 에이전트를 사용하여 텍스트를 요약합니다. """
        if not self.summarization_agent:
            return text_to_summarize
        try:
            summary_prompt = f"다음 대화 내용을 간결하게 핵심만 요약해줘. 이 요약은 나중에 대화의 맥락을 파악하는 데 사용될 거야.:\n\n{text_to_summarize}\n\n요약:"
            result = await Runner.run(self.summarization_agent, input=summary_prompt)
            summary = result.final_output.strip() if result.final_output else text_to_summarize
            return summary
        except Exception as e:
            logger.error(f"요약 중 오류 발생: {e}", exc_info=True)
            return text_to_summarize  # 요약 실패 시 원본 반환

    async def add_conversation_turn(self, speaker: str, message: str, previous_speaker: Optional[str] = None,
                                    previous_message: Optional[str] = None):
        """ 대화 턴(또는 요약본)을 메모리에 추가합니다. """
        self.turn_count += 1

        # 요약 대상 텍스트 구성
        if previous_message and previous_speaker:
            text_chunk = f"{previous_speaker}: {previous_message}\n{speaker}: {message}"
        else:
            text_chunk = f"{speaker}: {message}"

        # 요약 기능 사용 시 (self.summarization_agent가 None이 아니므로 이 블록이 실행됩니다)
        if self.summarization_agent:
            final_chunk_to_store = await self._summarize_text(text_chunk) # _summarize_text 함수가 호출됨
            logger.debug(f"RAG를 위해 요약된 대화 턴 저장 중: {final_chunk_to_store[:50]}...")
        else: # self.summarization_agent가 None일 경우 (이제 이 블록은 실행되지 않습니다)
            final_chunk_to_store = text_chunk
            logger.debug(f"RAG를 위해 원본 대화 턴 저장 중: {final_chunk_to_store[:50]}...")

        embedding = await get_openai_embedding(final_chunk_to_store)
        if embedding is not None:
            # FAISS는 add 시 2D 배열을 기대함
            self.index.add(np.array([embedding]))
            # 원본 텍스트와 메타데이터 저장, FAISS 인덱스와 동기화
            self.document_store.append({
                "text": final_chunk_to_store,
                "speaker": speaker,
                "turn_id": self.index.ntotal - 1,  # FAISS 내 ID
                "conversation_turn_count": self.turn_count  # 전체 대화에서의 턴 번호
            })
        else:
            logger.warning(f"다음 텍스트에 대한 임베딩 생성 실패: {final_chunk_to_store[:50]}...")

    async def get_relevant_context(self, query_message: str, k: Optional[int] = None) -> str:
        """ 쿼리 메시지와 관련된 과거 대화 컨텍스트를 검색합니다. """
        if self.index.ntotal == 0:
            return "관련된 과거 대화 기록이 아직 없습니다."

        k_to_use = k if k is not None else self.top_k
        k_to_use = min(k_to_use, self.index.ntotal)

        query_embedding = await get_openai_embedding(query_message)
        if query_embedding is None:
            logger.warning("RAG 쿼리에 대한 임베딩 생성 실패.")
            return "쿼리 임베딩 생성에 실패하여 과거 대화 기록을 가져올 수 없습니다."

        # FAISS search는 거리(D)와 인덱스(I)를 반환.
        # IndexFlatIP의 경우, 점수(내적값)가 높을수록 유사함 (정규화된 벡터의 경우 코사인 유사도).
        similarities, indices = self.index.search(np.array([query_embedding]), k_to_use)

        relevant_docs = []
        for i in range(len(indices[0])):
            doc_index = indices[0][i]  # 검색된 문서의 FAISS 인덱스
            similarity_score = similarities[0][i]  # 해당 문서와 쿼리 간의 유사도 점수
            if doc_index < len(self.document_store):  # 유효한 인덱스인지 확인
                doc = self.document_store[doc_index]
                # 저장된 텍스트는 요약본입니다.
                relevant_docs.append(
                    f"[과거 대화 기록 (Turn {doc.get('conversation_turn_count', 'N/A')}, 유사도 {similarity_score:.2f})]: {doc['text']}"
                )
            else:
                logger.warning(f"FAISS가 유효하지 않은 인덱스를 반환했습니다: {doc_index}")

        if not relevant_docs:
            return "관련된 과거 대화 기록을 찾지 못했습니다."

        return "\n\n".join(relevant_docs)


# --- 기존 Django Helper 함수들 (수정 없음) ---
async def save_chat_and_return(chat_room_id, from_company, to_company, contents) -> dict:
    chat = await Chat.objects.acreate(
        chat_room_id=chat_room_id,
        from_field_id=from_company.id, # 모델 필드명에 따라 from_company 대신 from_field 사용
        to_id=to_company.id,
        contents=contents
    )
    return {
        "id": chat.id,
        "fromId": from_company.id,
        "toId": to_company.id,
        "fromCompanyName": from_company.company_name,
        "toCompanyName": to_company.company_name,
        "contents": chat.contents,
        "roomId": chat_room_id,
        "createdAt": chat.created_at.isoformat(),
        "updatedAt": chat.updated_at.isoformat(),
    }


async def get_lead(lead_id: int, retries: int = 3, delay: float = 1.0) -> Optional[Lead]:
    for attempt in range(1, retries + 1):
        try:
            await sync_to_async(close_old_connections)()
            return await Lead.objects.select_related('lead_company', 'source_company').aget(id=lead_id)
        except Lead.DoesNotExist:
            logger.warning(f"ID={lead_id}인 리드를 찾을 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"리드 {lead_id} 조회 중 오류 발생 (시도 {attempt}): {e}", exc_info=True)
            if attempt < retries:
                await sync_to_async(close_old_connections)()
                await asyncio.sleep(delay)  # type: ignore
            else:
                raise  # 최대 재시도 후 예외 다시 발생


async def get_company(company_id):
    try:
        return await Company.objects.aget(id=company_id)
    except Company.DoesNotExist:
        logger.warning(f"ID={company_id}인 회사를 찾을 수 없습니다.")
        return None
    except Exception as e:
        logger.error(f"회사 {company_id} 조회 중 오류 발생: {e}", exc_info=True)
        raise


async def get_latest_summary(company):
    try:
        latest_file = await CompanyFile.objects.filter(company=company).order_by('-created_at').afirst()
        return latest_file.summary if latest_file else None
    except Exception as e:
        logger.error(f"회사 {company.id}의 최신 요약 정보 조회 중 오류 발생: {e}", exc_info=True)
        return None


async def create_chat_room(lead_id):
    try:
        return await ChatRoom.objects.acreate(lead_id=lead_id)
    except Exception as e:
        logger.error(f"리드 {lead_id}에 대한 채팅방 생성 중 오류 발생: {e}", exc_info=True)
        raise


# --- RAG가 적용된 메인 대화 함수 (OpenAI + FAISS) ---
async def run_agent_conversation(lead_id: int):
    """
    두 AI 에이전트(판매자, 구매자) 간의 RAG 기반 대화를 비동기적으로 실행하고,
    각 메시지를 데이터베이스에 저장 후 생성된 채팅 정보를 yield 합니다.
    OpenAI 임베딩과 FAISS를 RAG에 사용합니다. (openai >= 1.0.0 호환)
    """
    try:
        lead = await get_lead(lead_id)
        if not lead:
            logger.warning(f"ID={lead_id}인 리드를 찾을 수 없습니다.")
            yield {"error": f"리드 정보를 찾을 수 없습니다 (ID: {lead_id})."}
            return

        buyer_company_id = lead.lead_company_id
        seller_company_id = lead.source_company_id

        # get_company 함수는 ID를 받으므로 기존 코드 유지
        buyer_company = await get_company(buyer_company_id)
        seller_company = await get_company(seller_company_id)

        if not buyer_company or not seller_company:
            logger.error(f"리드 {lead_id}에 대한 구매자 또는 판매자 회사를 찾을 수 없습니다.")
            yield {"error": "구매자 또는 판매자 회사 정보를 찾을 수 없습니다."}
            return

        buyer_summary_from_db = await get_latest_summary(buyer_company)
        seller_summary_from_db = await get_latest_summary(seller_company)
        chat_room = await create_chat_room(lead_id)

    except Exception as e:
        logger.error(f"리드 {lead_id} 초기 데이터 로딩 중 오류 발생: {e}", exc_info=True)
        yield {"error": "초기 데이터 로딩 중 오류가 발생했습니다."}
        return

    try:
        # 요약 에이전트 인스턴스 생성
        summarizer_agent = Agent(name="SummarizerAgent",
                                 instructions="주어진 대화 내용을 다음 대화 참여자가 맥락을 이해하기 쉽도록 핵심만 간결하게 요약해.")

        # ConversationMemory 초기화 시 summarization_agent 전달
        conversation_memory = ConversationMemory(summarization_agent=summarizer_agent, top_k=2)

        # 판매자 에이전트 초기화
        seller_agent = Agent(
            name="SellerAgent",
            instructions=f"""
                    당신은 "{seller_company.company_name}" 회사 소속 영업 담당자입니다. 상대 회사가 필요로 할만한 제품을 추천하고 매출을 늘릴 수 있도록 설득하고 협상하세요.
                    대화 중 [과거 대화 기록]이 제공될 수 있습니다. 이를 참고하여 맥락에 맞는 답변을 생성하고, 동일한 제안이나 질문을 반복하지 마세요.
                    귀사 정보: {seller_summary_from_db if seller_summary_from_db else "제공된 요약 없음"}
                    상대 회사 정보: {buyer_summary_from_db if buyer_summary_from_db else "제공된 요약 없음"}
                    **대화 규칙:**
                    1. 구체적인 수치는 사실 기반으로, 그 외 효과 및 장점은 자유롭게 답변하세요.
                    2. 반드시 한국어로 대답하세요.
                    """,
        )
        # 구매자 에이전트 초기화
        buyer_agent = Agent(
            name="BuyerAgent",
            instructions=f"""
                    당신은 "{buyer_company.company_name}" 회사 소속 구매 담당자입니다. 상대방의 제안이 적합한지 질문하고 협상하세요.
                    대화 중 [과거 대화 기록]이 제공될 수 있습니다. 이를 반드시 참고하여 동일한 질문을 반복하지 마세요.
                    적합하다고 판단되면 구매 의사를 적합성(%)과 함께 "종료"라고 명확히 대답하세요.
                    귀사 정보: {buyer_summary_from_db if buyer_summary_from_db else "제공된 요약 없음"}
                    **대화 규칙:**
                    1. [과거 대화 기록]을 참고하여 중복 질문을 피하세요.
                    2. 상대 제안을 회사 필요와 비교 분석하여 장단점을 평가하세요.
                    3. 제품 기능 외 가격, 납기, 지원 조건 등 실질적 구매 조건을 확인하세요.
                    4. 제안이 적합하면, **적합성(0%~100%)과 근거를 밝히고 "종료"** 라고 답변하세요. (예: "제안이 요구사항과 85% 일치하며 가격 경쟁력이 뛰어납니다. 구매 검토하겠습니다. 종료")
                    5. 적합성은 보수적으로 측정하고, 반드시 한국어로 대답하세요.
                    """,
        )

    except Exception as e:
        logger.error(f"리드 {lead_id} 에이전트 초기화 중 오류 발생: {e}", exc_info=True)
        yield {"error": "AI 에이전트 초기화 중 오류가 발생했습니다."}
        return

    seller_message_content = ""
    buyer_message_content = ""
    # 이전 메시지 추적 변수 초기화
    previous_seller_message_for_memory = ""
    previous_buyer_message_for_memory = ""

    try:
        # 판매자 첫 메시지 생성
        seller_result = await Runner.run(seller_agent, input="상대 회사에게 우리 회사의 제품을 제안하세요.")
        seller_message_content = seller_result.final_output.strip() if seller_result.final_output else "판매자 첫 제안 생성 실패"
    except Exception as e:
        logger.error(f"리드 {lead_id} 초기 판매자 에이전트 실행 중 오류 발생: {e}", exc_info=True)
        seller_message_content = "오류로 인해 첫 제안을 생성할 수 없습니다."

    try:
        # 판매자 첫 메시지 저장 및 yield
        seller_chat_data = await save_chat_and_return(
            chat_room_id=chat_room.id,
            from_company=seller_company,
            to_company=buyer_company,
            contents=seller_message_content
        )
        yield seller_chat_data
    except Exception as e:
        logger.error(f"리드 {lead_id} 초기 판매자 채팅 저장 중 오류 발생: {e}", exc_info=True)
        yield {"error": "첫 메시지 저장 중 오류가 발생했습니다."}
        # 첫 메시지 저장 실패 시 대화 진행 의미 없음
        return

    # 첫 메시지를 메모리에 추가 (이때 요약 기능이 활성화되어 있다면 _summarize_text 호출됨)
    await conversation_memory.add_conversation_turn(
        speaker="SellerAgent",
        message=seller_message_content,
        previous_speaker=None, # 첫 턴이므로 이전 메시지 없음
        previous_message=None
    )
    previous_seller_message_for_memory = seller_message_content # 다음 턴에서 이전 메시지로 사용

    conversation_ended = False
    # 원본 코드에 있던 3턴 루프 유지
    for turn in range(3):
        # --- 구매자 턴 ---
        try:
            relevant_context_for_buyer = await conversation_memory.get_relevant_context(
                previous_seller_message_for_memory)
            buyer_input_prompt = f"{relevant_context_for_buyer}\n\n---\n위의 과거 대화 기록을 참고하여 다음 판매자 메시지에 응답하세요:\nSellerAgent: {previous_seller_message_for_memory}"
            buyer_result = await Runner.run(buyer_agent, input=buyer_input_prompt)
            buyer_message_content = buyer_result.final_output.strip() if buyer_result.final_output else "구매자 답변 생성 실패"
        except Exception as e:
            logger.error(f"리드 {lead_id} 구매자 에이전트 실행 중 오류 발생 (턴 {turn + 1}): {e}", exc_info=True)
            buyer_message_content = "오류로 인해 답변할 수 없습니다."

        try:
            # 구매자 메시지 저장 및 yield
            buyer_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=buyer_company,
                to_company=seller_company,
                contents=buyer_message_content
            )
            yield buyer_chat_data
        except Exception as e:
            logger.error(f"리드 {lead_id} 구매자 채팅 저장 중 오류 발생 (턴 {turn + 1}): {e}", exc_info=True)
            break # 저장 실패 시 루프 종료

        # 현재 턴 (판매자 메시지 + 구매자 메시지)을 메모리에 추가 (이때 요약 기능이 활성화)
        await conversation_memory.add_conversation_turn(
            speaker="BuyerAgent",
            message=buyer_message_content,
            previous_speaker="SellerAgent",
            previous_message=previous_seller_message_for_memory # 바로 이전 턴의 판매자 메시지
        )
        previous_buyer_message_for_memory = buyer_message_content # 다음 턴에서 이전 메시지로 사용

        # 구매자 메시지에 '종료' 포함 시 대화 종료
        if "종료" in buyer_message_content:
            conversation_ended = True
            break # 루프 종료

        # --- 판매자 턴 ---
        # (만약 구매자 메시지에 '종료'가 없으면 판매자가 응답)
        try:
            relevant_context_for_seller = await conversation_memory.get_relevant_context(
                previous_buyer_message_for_memory)
            seller_input_prompt = f"{relevant_context_for_seller}\n\n---\n위의 과거 대화 기록을 참고하여 다음 구매자 메시지에 응답하세요:\nBuyerAgent: {previous_buyer_message_for_memory}"
            seller_result = await Runner.run(seller_agent, input=seller_input_prompt)
            seller_message_content = seller_result.final_output.strip() if seller_result.final_output else "판매자 답변 생성 실패"
        except Exception as e:
            logger.error(f"리드 {lead_id} 판매자 에이전트 실행 중 오류 발생 (턴 {turn + 1}): {e}", exc_info=True)
            seller_message_content = "오류로 인해 답변할 수 없습니다."

        try:
            # 판매자 메시지 저장 및 yield
            seller_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=seller_company,
                to_company=buyer_company,
                contents=seller_message_content
            )
            yield seller_chat_data
        except Exception as e:
            logger.error(f"리드 {lead_id} 판매자 채팅 저장 중 오류 발생 (턴 {turn + 1}): {e}", exc_info=True)
            break # 저장 실패 시 루프 종료

        # 현재 턴 (구매자 메시지 + 판매자 메시지)을 메모리에 추가 (이때 요약 기능이 활성화)
        await conversation_memory.add_conversation_turn(
            speaker="SellerAgent",
            message=seller_message_content,
            previous_speaker="BuyerAgent",
            previous_message=previous_buyer_message_for_memory # 바로 이전 턴의 구매자 메시지
        )
        previous_seller_message_for_memory = seller_message_content # 다음 턴에서 이전 메시지로 사용

        # 판매자 메시지에 '종료' 포함 시 대화 종료 (원본 코드 로직 유지)
        if "종료" in seller_message_content:
            conversation_ended = True
            break # 루프 종료

    # --- 대화 종료 또는 최대 턴 도달 후 최종 요약 (구매자 관점) ---
    if not conversation_ended:
        final_summary_context_query = buyer_message_content
        if not final_summary_context_query:
            final_summary_context_query = previous_buyer_message_for_memory if previous_buyer_message_for_memory else previous_seller_message_for_memory

        relevant_context_for_final_summary = await conversation_memory.get_relevant_context(final_summary_context_query,
                                                                                            k=5)
        summary_request_input = (
            f"{relevant_context_for_final_summary}\n\n---\n"
            f"위의 과거 대화 기록과 현재까지의 논의를 종합하여, 우리 회사({buyer_company.company_name}) 입장에서의 "
            f"최종 적합성(0% ~ 100%)과 그 판단 근거를 명확하게 밝혀주세요. "
            f"만약 추가 정보가 필요하다면 어떤 정보가 필요한지도 언급해주세요."
            f"적합성은 최대한 보수적으로 측정하세요."
        )
        logger.debug(f"리드 {lead_id} 최종 요약 입력 프롬프트:\n{summary_request_input[:500]}...")

        try:
            final_summary_result = await Runner.run(buyer_agent, input=summary_request_input)
            final_summary_message = final_summary_result.final_output.strip() if final_summary_result.final_output else "최종 요약 생성 실패"
        except Exception as e:
            logger.error(f"리드 {lead_id} 최종 요약 에이전트 실행 중 오류 발생: {e}", exc_info=True)
            final_summary_message = "오류로 인해 대화 요약을 생성할 수 없습니다."

        try:
            final_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=buyer_company,
                to_company=seller_company,
                contents=final_summary_message
            )
            yield final_chat_data
        except Exception as e:
            logger.error(f"리드 {lead_id} 최종 요약 채팅 저장 중 오류 발생: {e}", exc_info=True)
            yield {"error": "최종 요약 저장 중 오류가 발생했습니다."}