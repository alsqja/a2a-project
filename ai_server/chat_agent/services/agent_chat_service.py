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
                """,
    )

    seller_message = "저희 제품/서비스에 대해 제안드릴 것이 있어 연락드렸습니다."

    conversation_history = [f"SellerAgent: {seller_message}"]
    print(f"0. seller message: {seller_message} \n\n")

    is_success = 1
    for turn in range(10):
        try:
            buyer_result = await Runner.run(buyer_agent, input=seller_message)
            buyer_message = buyer_result.final_output.strip() if buyer_result.final_output else "buyer 답변 생성 실패"
        except Exception as e:
            print(f"Error running BuyerAgent: {e}")
            buyer_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"BuyerAgent: {buyer_message}")
        print(f"{turn + 1}. Buyer ({buyer_company.company_name}): {buyer_message} \n\n --------------------- \n\n")

        await save_chat(
            chat_room_id=chat_room.id,
            from_id=buyer_company.id,
            to_id=seller_company.id,
            contents=buyer_message
        )

        if "종료" in buyer_message:
            print("Buyer decided to end the conversation.")
            is_success = 0
            break

        seller_input = "\n".join(conversation_history)

        try:
            seller_result = await Runner.run(seller_agent, input=seller_input)
            seller_message = seller_result.final_output.strip() if seller_result.final_output else "seller 답변 생성 실패"
        except Exception as e:
            print(f"Error running SellerAgent: {e}")
            seller_message = "오류로 인해 답변할 수 없습니다."

        conversation_history.append(f"SellerAgent: {seller_message}")
        print(f"{turn + 1}. Seller ({seller_company.company_name}): {seller_message} \n\n --------------------- \n\n")
        await save_chat(
            chat_room_id=chat_room.id,
            from_id=seller_company.id,
            to_id=buyer_company.id,
            contents=seller_message
        )

        if "종료" in seller_message:
            print("Seller decided to end the conversation.")
            is_success = 0
            break

    if is_success == 1:
        total_input = "\n".join(conversation_history)

        total_result = await Runner.run(buyer_agent, input = total_input + "\n 이 대화 내용을 토대로 적합성(0% ~ 100%)과 판단 근거를 명확하게 밝혀주세요.")
        total_message = total_result.final_output.strip() if total_result.final_output else "total 답변 생성 실패"

        print(f"total: {total_message}")

        await save_chat(
            chat_room_id=chat_room.id,
            from_id=buyer_company.id,
            to_id=seller_company.id,
            contents=total_message
        )


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