import asyncio
import logging
from agents import Agent, Runner

from chat_agent.models import Company, CompanyFile, Lead, Chat, ChatRoom

# 로거 설정
logger = logging.getLogger(__name__)

async def run_agent_conversation(lead_id):
    """
    두 AI 에이전트(Seller, Buyer) 간의 대화를 비동기적으로 실행하고,
    각 메시지를 데이터베이스에 저장 후 생성된 채팅 정보를 yield 합니다.
    """
    try:
        # 1. 초기 데이터 비동기 조회
        lead = await get_lead(lead_id)
        if not lead:
            logger.warning(f"Lead not found for id: {lead_id}")
            return # 리드가 없으면 종료

        # lead 객체에서 관련 회사 ID를 가져옵니다.
        # (모델 필드명은 실제 모델 정의에 따라 다를 수 있습니다.)
        buyer_company_id = lead.lead_company_id
        seller_company_id = lead.source_company_id

        # 회사 정보와 최신 요약 정보를 비동기적으로 조회합니다.
        # asyncio.gather를 사용하면 병렬로 처리할 수 있지만,
        # 여기서는 순차적으로 처리해도 큰 문제 없을 시 가독성을 위해 순차 처리합니다.
        buyer_company = await get_company(buyer_company_id)
        seller_company = await get_company(seller_company_id)

        if not buyer_company or not seller_company:
             logger.error(f"Buyer or Seller company not found for lead: {lead_id}")
             return # 회사를 찾을 수 없으면 종료

        buyer_summary = await get_latest_summary(buyer_company)
        seller_summary = await get_latest_summary(seller_company)

        # 채팅방 생성 또는 조회 (여기서는 생성 로직만 있음)
        chat_room = await create_chat_room(lead_id)

    except Exception as e:
        logger.error(f"Error fetching initial data for lead {lead_id}: {e}", exc_info=True)
        # 초기 데이터 로딩 실패 시 적절한 에러 메시지 yield 또는 다른 처리
        yield {"error": "초기 데이터 로딩 중 오류가 발생했습니다."}
        return

    # 2. 에이전트 초기화
    try:
        seller_agent = Agent(
            name="SellerAgent",
            instructions=f"""
                    당신은 "{seller_company.company_name}" 회사 소속 영업 담당자입니다. 상대 회사가 필요로 할만한 제품을 추천하고 매출을 늘릴 수 있도록 설득하고 협상하세요.
                    회사 정보는 다음과 같습니다.\n\n
                    {seller_summary if seller_summary else "회사 정보 요약 없음"}
                    \n\n
                    상대 회사의 정보를 통해 니즈를 파악해 적절한 제안을 하세요.
                    상대방이 질문을 한다면 질문에 답변하세요.
                    상대 회사의 정보는 다음과 같습니다.\n\n
                    {buyer_summary if buyer_summary else "회사 정보 요약 없음"}

                    **대화 규칙:**
                    1. 답변 과정에서 구체적인 수치에 관한 정보는 사실만 포함하세요.
                    2. 그 외 기대 효과, 장점 등 추상적인 부분은 데이터에 기반해 자유롭게 대답하세요.
                    3. 반드시 한국어로 대답하세요.
                    """,
        )
        buyer_agent = Agent(
            name="BuyerAgent",
            instructions=f"""
                    당신은 "{buyer_company.company_name}" 회사 소속 구매 담당자입니다. 상대방이 제공하는 제품이 우리에게 적합한지 질문을 통해 파악하고 협상하세요.
                    적합하다고 판단되면 구매 의사를 적합성(%) 과 함께 "종료" 라고 대답하세요.
                    회사 정보는 다음과 같습니다.\n\n
                    {buyer_summary if buyer_summary else "회사 정보 요약 없음"}

                    **대화 규칙:**
                    1. 이전 대화 내용을 반드시 참고하여 동일한 질문을 반복하지 마세요.
                    2. 상대방의 제안이 우리 회사의 필요(위의 회사 정보 참고)와 얼마나 일치하는지 구체적인 장단점을 분석하며 평가하세요.
                    3. 단순히 제품 기능만 묻지 말고, 가격, 납기, 지원 조건 등 실질적인 구매 조건을 확인하세요.
                    4. 제안이 적합하다고 판단되면, **적합성(0%~100%)과 판단 근거를 명확히 밝히고** "종료" 라고 명확히 포함하여 대답하세요. (예: "제안해주신 내용이 저희의 요구사항과 85% 일치하며, 특히 가격 경쟁력이 뛰어나다고 판단됩니다. 구매를 긍정적으로 검토하겠습니다. 종료")
                    5. 적합성은 최대한 보수적으로 측정하세요.
                    6. 반드시 한국어로 대답하세요.
                    """,
        )
    except Exception as e:
        logger.error(f"Error initializing agents for lead {lead_id}: {e}", exc_info=True)
        yield {"error": "AI 에이전트 초기화 중 오류가 발생했습니다."}
        return

    # 3. 초기 Seller 메시지 생성 및 전송
    try:
        seller_result = await Runner.run(seller_agent, input="상대 회사에게 우리 회사의 제품을 제안하세요.")
        seller_message = seller_result.final_output.strip() if seller_result.final_output else "seller 첫 제안 생성 실패"
    except Exception as e:
        logger.error(f"Error running initial seller agent for lead {lead_id}: {e}", exc_info=True)
        seller_message = "오류로 인해 첫 제안을 생성할 수 없습니다."

    conversation_history = [f"SellerAgent: {seller_message}"]

    try:
        # 최초 seller 메시지 저장 및 yield (개선된 함수 사용)
        seller_chat_data = await save_chat_and_return(
            chat_room_id=chat_room.id,
            from_company=seller_company, # 객체 전달
            to_company=buyer_company,     # 객체 전달
            contents=seller_message
        )
        yield seller_chat_data
    except Exception as e:
         logger.error(f"Error saving initial seller chat for lead {lead_id}: {e}", exc_info=True)
         yield {"error": "첫 메시지 저장 중 오류가 발생했습니다."}
         return


    # 4. 대화 루프 진행 (최대 10턴)
    conversation_ended = False
    for turn in range(10): # 최대 10턴 진행
        # Buyer 턴
        try:
            buyer_result = await Runner.run(buyer_agent, input=seller_message) # 이전 seller 메시지를 input으로
            buyer_message = buyer_result.final_output.strip() if buyer_result.final_output else "buyer 답변 생성 실패"
        except Exception as e:
            logger.error(f"Error running buyer agent turn {turn+1} for lead {lead_id}: {e}", exc_info=True)
            buyer_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"BuyerAgent: {buyer_message}")

        try:
            buyer_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=buyer_company,
                to_company=seller_company,
                contents=buyer_message
            )
            yield buyer_chat_data
        except Exception as e:
            logger.error(f"Error saving buyer chat turn {turn+1} for lead {lead_id}: {e}", exc_info=True)
            # 에러 발생 시 루프 중단 또는 다음 턴 진행 결정 필요
            break

        if "종료" in buyer_message:
            conversation_ended = True
            break

        # Seller 턴
        seller_input = "\n".join(conversation_history) # 전체 대화 내역을 input으로
        try:
            seller_result = await Runner.run(seller_agent, input=seller_input)
            seller_message = seller_result.final_output.strip() if seller_result.final_output else "seller 답변 생성 실패"
        except Exception as e:
            logger.error(f"Error running seller agent turn {turn+1} for lead {lead_id}: {e}", exc_info=True)
            seller_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"SellerAgent: {seller_message}")

        try:
            seller_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=seller_company,
                to_company=buyer_company,
                contents=seller_message
            )
            yield seller_chat_data
        except Exception as e:
            logger.error(f"Error saving seller chat turn {turn+1} for lead {lead_id}: {e}", exc_info=True)
            # 에러 발생 시 루프 중단 또는 다음 턴 진행 결정 필요
            break

        if "종료" in seller_message: # Seller가 종료를 언급하는 경우는 드물겠지만 추가
            conversation_ended = True
            break

    # 5. 루프 종료 후 최종 요약 (Buyer가 "종료"하지 않았을 경우)
    if not conversation_ended:
        total_input = "\n".join(conversation_history)
        summary_request_input = total_input + "\n\n---\n이 대화 내용을 토대로 최종적으로 저희 회사 입장에서의 적합성(0% ~ 100%)과 그 판단 근거를 명확하게 밝혀주세요."

        try:
            final_summary_result = await Runner.run(
                buyer_agent,
                input=summary_request_input
            )
            final_summary_message = final_summary_result.final_output.strip() if final_summary_result.final_output else "최종 요약 생성 실패"
        except Exception as e:
            logger.error(f"Error running final summary agent for lead {lead_id}: {e}", exc_info=True)
            final_summary_message = "오류로 인해 대화 요약을 생성할 수 없습니다."

        try:
            final_chat_data = await save_chat_and_return(
                chat_room_id=chat_room.id,
                from_company=buyer_company, # 요약은 Buyer가 하는 것으로 간주
                to_company=seller_company,
                contents=final_summary_message
            )
            yield final_chat_data
        except Exception as e:
            logger.error(f"Error saving final summary chat for lead {lead_id}: {e}", exc_info=True)
            yield {"error": "최종 요약 저장 중 오류가 발생했습니다."}


# --- Helper Functions (Async ORM 사용) ---

async def save_chat_and_return(chat_room_id, from_company, to_company, contents) -> dict:
    """
    채팅 메시지를 비동기적으로 저장하고, 필요한 정보를 포함한 dict를 반환합니다.
    Company 객체를 직접 받아 불필요한 DB 조회를 줄입니다.
    """
    chat = await Chat.objects.acreate(
        chat_room_id=chat_room_id,
        from_field_id=from_company.id,
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

async def get_lead(lead_id: int, retries: int = 3, delay: float = 1.0) -> Lead | None:
    """지정된 ID의 Lead 객체를 비동기적으로 가져옵니다. 일반 예외에 대해 재시도합니다."""
    for attempt in range(1, retries + 1):
        try:
            return await Lead.objects.select_related('lead_company', 'source_company').aget(id=lead_id)
        except Lead.DoesNotExist:
            logger.warning(f"Lead with id={lead_id} does not exist.")
            return None
        except Exception as e:
            logger.error(f"Error fetching lead {lead_id} (attempt {attempt}): {e}", exc_info=True)
            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                raise  # 재시도 실패 후 최종 에러는 상위로 전달

async def get_company(company_id):
    """지정된 ID의 Company 객체를 비동기적으로 가져옵니다."""
    try:
        return await Company.objects.aget(id=company_id)
    except Company.DoesNotExist:
        logger.warning(f"Company with id={company_id} does not exist.")
        return None
    except Exception as e:
        logger.error(f"Error fetching company {company_id}: {e}", exc_info=True)
        raise

async def get_latest_summary(company):
    """주어진 Company 객체에 대한 가장 최신 CompanyFile의 요약을 비동기적으로 가져옵니다."""
    try:
        latest_file = await CompanyFile.objects.filter(company=company).order_by('-created_at').afirst()
        return latest_file.summary if latest_file else None
    except Exception as e:
        logger.error(f"Error fetching latest summary for company {company.id}: {e}", exc_info=True)
        return None

async def create_chat_room(lead_id):
    """지정된 lead_id로 ChatRoom 객체를 비동기적으로 생성합니다."""
    try:
        # 이미 존재하는지 확인하고 생성하거나 가져오는 로직(get_or_create)도 고려 가능
        return await ChatRoom.objects.acreate(lead_id=lead_id)
    except Exception as e:
        logger.error(f"Error creating chat room for lead {lead_id}: {e}", exc_info=True)
        raise
