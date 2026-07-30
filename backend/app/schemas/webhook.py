from pydantic import BaseModel
from uuid import UUID


class VexaWebhookPayload(BaseModel):
    event:      str       # "bot.joined" | "bot.left" | "bot.failed"
    meeting_id: UUID