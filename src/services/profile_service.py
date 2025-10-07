import asyncio
from src.config.settings import settings
from supabase import acreate_client, AClient, AsyncClientOptions
from src.schemas import Profile
from typing import Optional
from src.utils import AsyncMixin


class ProfileService(AsyncMixin):
    async def __ainit__(self):
        self.supabase: AClient = await acreate_client(
            settings.supabase.supabase_url, settings.supabase.supabase_service_key, options=AsyncClientOptions(schema='myaso'))

    async def add_profile(self, form_data: Profile):
        result = await self.supabase.table('clients').insert(form_data.model_dump()).execute()
        return result

    async def get_profile(self, client_phone: str):
        result = await self.supabase.table('clients').select('*').eq('phone', client_phone).execute()
        return result.data[0] if len(result.data) else []
