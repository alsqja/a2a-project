from agents import Agent, Runner


async def chat_summary(chats, source_company, lead_company) -> str:
    summary_agent = Agent(
        name="SummaryAgent",
        instructions=f"""
                당신은 "{source_company.company_name}" 회사 소속 영업 담당자 입니다.
                "{lead_company.company_name}" 회사 소속 buyer 와의 협상 내용을 보고해야 합니다.
                대화 내역을 요약하고 마크다운 형식의 보고서를 출력하세요.
                
                **보고서 규칙**
                1. 반드시 한국어로 작성할 것
                2. 대화 내용을 요약하고 구매자의 니즈를 분석할 것
                """,
    )

    chat_input = "\n".join(chats)
    summary_result = await Runner.run(summary_agent, chat_input)
    summary_message = summary_result.final_output.strip() if summary_result.final_output else "대화 내용 요약 실패"

    return summary_message