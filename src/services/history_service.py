from src.config.settings import settings
from supabase import acreate_client, AClient, AsyncClientOptions
from src.schemas import Message, ConversationHistoryMessage
from typing import Optional
from src.utils import AsyncMixin
import re

class HistoryService(AsyncMixin):
    async def __ainit__(self):
        self.supabase: AClient = await acreate_client(
            settings.supabase.supabase_url, settings.supabase.supabase_service_key, options=AsyncClientOptions(schema='myaso'))

    async def get_history(self, client_phone: str) -> list[Message]:
        response = await self.supabase.table('conversation_history').select('*').eq('client_phone', client_phone).order('created_at', desc=False).execute()
        return response

    async def get_instructions(self, topic: str):
        topic =  re.sub(r'\s*\([^)]*\)', '', topic).strip()
        response = await self.supabase.table('prompts').select('*').eq('topic', topic).execute()
        return response.data[0] if len(response.data) else []


    async def add_message_to_conversation_history(self, message: ConversationHistoryMessage):
        message_dict = message.model_dump()
        
        result = await self.supabase.table('conversation_history').insert(message_dict).execute()
        return result

    async def delete_conversation_history(self, client_phone: str):
        print('delete_conversation_history', client_phone)
        await self.supabase.table('conversation_history').delete().eq('client_phone', client_phone).execute()