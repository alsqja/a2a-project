from openai import OpenAI
from ..models import ChatRoom, Company, CompanyFile, Chat
from django.conf import settings


class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def send_message(self, company_id, contents, room_id = None):
        # company_id 기반 Company 객체 가져오기
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise ValueError(f"Company with ID {company_id} does not exist")

        # CompanyFile에서 summary 가져오기
        summary = CompanyFile.objects.filter(company=company).order_by('-created_at').first()
        summary_text = summary.summary if summary else "No summary available."

        # room_id가 없는 경우 새로운 ChatRoom 생성
        if room_id is None:
            chat_room = ChatRoom.objects.create()
            room_id = chat_room.id
        else:
            # 존재하는 ChatRoom 가져오기 (없는 경우 예외 처리)
            try:
                chat_room = ChatRoom.objects.get(id=room_id)
            except ChatRoom.DoesNotExist:
                raise ValueError(f"ChatRoom with ID {room_id} does not exist")

        # GPT-4o 호출
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"너는 B2B 세일즈를 도와주는 AI야 회사 요약 정보를 바탕으로 적절한 대답을 해줘. 다음은 회사 요약 정보야:\n\n{summary_text}"
                },
                {
                    "role": "user",
                    "content": contents
                }
            ],
            temperature=0.7,
        )

        ai_reply = response.choices[0].message.content.strip()

        chat = Chat.objects.create(contents=ai_reply, chat_room_id=room_id, to_id=company_id)

        return {
            "room_id": room_id,
            "contents": ai_reply,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "id": chat.id,
        }
