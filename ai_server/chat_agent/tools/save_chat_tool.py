from agents import FunctionTool, function_tool
from pydantic import BaseModel

from chat_agent.models import Chat


class ChatLogArgs(BaseModel):
    chat_room_id: int
    from_id: int
    to_id: int
    contents: str

@function_tool
async def save_chat_log(args: ChatLogArgs) -> str:
    Chat.objects.create(
        chat_room_id=args.chat_room_id,
        from_field_id=args.from_id,
        to_id=args.to_id,
        contents=args.contents
    )
    return "saved"
