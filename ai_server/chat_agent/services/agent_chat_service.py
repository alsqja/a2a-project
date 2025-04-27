from agents import Agent, Runner
from asgiref.sync import sync_to_async

from chat_agent.models import Company, CompanyFile, Lead, Chat, ChatRoom


async def run_agent_conversation(lead_id):
    lead = await get_lead(lead_id)

    buyer_company = await get_company((await get_lead_company(lead)).id)
    seller_company = await get_company((await get_source_company(lead)).id)

    buyer_summary = await get_latest_summary(buyer_company)
    seller_summary = await get_latest_summary(seller_company)

    chat_room = await create_chat_room(lead_id)

    seller_agent = Agent(
        name="SellerAgent",
        instructions=f"""
                당신은 "{seller_company.company_name}" 회사 소속 영업 담당자입니다. 상대 회사가 필요로 할만한 제품을 추천하고 매출을 늘릴 수 있도록 설득하고 협상하세요.
                회사 정보는 다음과 같습니다.\n\n
                {seller_summary}
                \n\n
                상대 회사의 정보를 통해 니즈를 파악해 적절한 제안을 하세요.
                상대방이 질문을 한다면 질문에 답변하세요.
                상대 회사의 정보는 다음과 같습니다.\n\n
                {buyer_summary}
                
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
                {buyer_summary}

                **대화 규칙:**
                1. 이전 대화 내용을 반드시 참고하여 동일한 질문을 반복하지 마세요.
                2. 상대방의 제안이 우리 회사의 필요(위의 회사 정보 참고)와 얼마나 일치하는지 구체적인 장단점을 분석하며 평가하세요.
                3. 단순히 제품 기능만 묻지 말고, 가격, 납기, 지원 조건 등 실질적인 구매 조건을 확인하세요.
                4. 제안이 적합하다고 판단되면, **적합성(0%~100%)과 판단 근거를 명확히 밝히고** "종료" 라고 명확히 포함하여 대답하세요. (예: "제안해주신 내용이 저희의 요구사항과 85% 일치하며, 특히 가격 경쟁력이 뛰어나다고 판단됩니다. 구매를 긍정적으로 검토하겠습니다. 종료")
                5. 반드시 한국어로 대답하세요.
                """,
    )

    seller_result = await Runner.run(seller_agent, input="상대 회사에게 우리 회사의 제품을 제안하세요.")
    seller_message = seller_result.final_output.strip() if seller_result.final_output else "seller 첫 제안 생성 실패"

    conversation_history = [f"SellerAgent: {seller_message}"]

    # 최초 seller 메세지 저장 및 yield
    seller_chat = await save_chat_and_return(
        chat_room_id=chat_room.id,
        from_id=seller_company.id,
        to_id=buyer_company.id,
        contents=seller_message
    )
    yield seller_chat

    is_success = 1
    for turn in range(10):
        try:
            buyer_result = await Runner.run(buyer_agent, input=seller_message)
            buyer_message = buyer_result.final_output.strip() if buyer_result.final_output else "buyer 답변 생성 실패"
        except Exception as e:
            buyer_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"BuyerAgent: {buyer_message}")

        buyer_chat = await save_chat_and_return(
            chat_room_id=chat_room.id,
            from_id=buyer_company.id,
            to_id=seller_company.id,
            contents=buyer_message
        )
        yield buyer_chat

        if "종료" in buyer_message:
            is_success = 0
            break

        seller_input = "\n".join(conversation_history)

        try:
            seller_result = await Runner.run(seller_agent, input=seller_input)
            seller_message = seller_result.final_output.strip() if seller_result.final_output else "seller 답변 생성 실패"
        except Exception as e:
            seller_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"SellerAgent: {seller_message}")

        seller_chat = await save_chat_and_return(
            chat_room_id=chat_room.id,
            from_id=seller_company.id,
            to_id=buyer_company.id,
            contents=seller_message
        )
        yield seller_chat

        if "종료" in seller_message:
            is_success = 0
            break

    if is_success == 1:
        total_input = "\n".join(conversation_history)

        try:
            total_result = await Runner.run(
                buyer_agent,
                input=total_input + "\n 이 대화 내용을 토대로 적합성(0% ~ 100%)과 판단 근거를 명확하게 밝혀주세요."
            )
            total_message = total_result.final_output.strip() if total_result.final_output else "total 답변 생성 실패"
        except Exception:
            total_message = "대화 요약을 실패했습니다."

        total_chat = await save_chat_and_return(
            chat_room_id=chat_room.id,
            from_id=buyer_company.id,
            to_id=seller_company.id,
            contents=total_message
        )
        yield total_chat


@sync_to_async
def save_chat(chat_room_id, from_id, to_id, contents) -> str:
    Chat.objects.create(
        chat_room_id=chat_room_id,
        from_field_id=from_id,
        to_id=to_id,
        contents=contents
    )
    return "saved"


@sync_to_async
def save_chat_and_return(chat_room_id, from_id, to_id, contents) -> dict:
    chat = Chat.objects.create(
        chat_room_id=chat_room_id,
        from_field_id=from_id,
        to_id=to_id,
        contents=contents
    )
    from_company = Company.objects.get(id=from_id)
    to_company = Company.objects.get(id=to_id)

    return {
        "id": chat.id,
        "fromId": from_company.id,
        "toId": to_company.id,
        "fromCompanyName": from_company.company_name,
        "toCompanyName": to_company.company_name,
        "contents": chat.contents,
        "createdAt": chat.created_at.isoformat(),
        "updatedAt": chat.updated_at.isoformat(),
    }


@sync_to_async
def get_lead(lead_id):
    return Lead.objects.get(id=lead_id)


@sync_to_async
def get_company(company_id):
    return Company.objects.get(id=company_id)


@sync_to_async
def get_latest_summary(company):
    return CompanyFile.objects.filter(company=company).order_by('-created_at').first().summary


@sync_to_async
def get_lead_company(lead):
    return lead.lead_company


@sync_to_async
def get_source_company(lead):
    return lead.source_company


@sync_to_async
def create_chat_room(lead_id):
    return ChatRoom.objects.create(
        lead_id=lead_id,
    )
