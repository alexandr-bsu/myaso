import asyncio
from src.config.settings import settings
from supabase import acreate_client, AClient, AsyncClientOptions
from typing import Optional
from src.utils import AsyncMixin


class OrderService(AsyncMixin):
    async def __ainit__(self):
        self.supabase: AClient = await acreate_client(
            settings.supabase.supabase_url, settings.supabase.supabase_service_key, options=AsyncClientOptions(schema='myaso'))


    async def get_all_products(self):
        result = await self.supabase.table('products').select('*').execute()
        return result.data if len(result.data) else []

    async def get_all_orders_by_client_phone(self, client_phone: str):
        result = await self.supabase.table('orders').select('*').eq('client_phone', client_phone).execute()
        return result.data if len(result.data) else []

    async def get_sys_variables(self):
        result = await self.supabase.table('system').select('*').execute()
        return result.data if len(result.data) else []
        