from asgiref.sync import sync_to_async

from chat_agent.agents.chat_summary_agent import chat_summary
from chat_agent.models import ChatRoom, Lead, Chat


async def create_chat_summary(chat_room_id, lead_id):
    chats = await get_chats(chat_room_id)
    source_company = await get_chat_room_source_company(lead_id)
    lead_company = await get_chat_room_lead_company(lead_id)

    agent_result = await chat_summary(chats, source_company, lead_company)

    return {
        "summary": agent_result,
    }

@sync_to_async
def get_chats(chat_room_id):
    chats = Chat.objects.filter(chat_room_id=chat_room_id)
    chat_list = []
    for chat in chats:
        chat_list.append(chat.contents)

    return chat_list

@sync_to_async
def get_chat_room_source_company(lead_id):
    return Lead.objects.get(id=lead_id).source_company

@sync_to_async
def get_chat_room_lead_company(lead_id):
    return Lead.objects.get(id=lead_id).lead_company