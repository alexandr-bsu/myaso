from token import OP
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Dict, Any
from src.config.settings import settings
import json


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: str


class ConversationHistoryMessage(BaseModel):
    message: str
    role: str
    client_phone: str


class InitConverastionRequest(BaseModel):
    client_phone: str


class DirectMessageRequest(BaseModel):
    client_phone: str
    message: str
    
class UserMessageRequest(InitConverastionRequest):
    message: str

class LLMRequest(BaseModel):
    prompt: Optional[str] = None
    client_phone: str
    
    @field_validator('prompt', mode='before')
    @classmethod
    def validate_prompt_json(cls, v):
        if isinstance(v, str):
            try:
                return json.dumps(json.loads(v))
            except (json.JSONDecodeError, TypeError):
                return json.dumps(v)
        return v


class Profile(BaseModel):
    client_phone: str
    # Добавьте другие поля профиля по необходимости
    

class ResetConversationRequest(BaseModel):
    client_phone: str