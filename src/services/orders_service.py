import asyncio
import asyncpg

from src.config.settings import settings
from supabase import acreate_client, AClient, AsyncClientOptions
from typing import Optional
from src.utils import AsyncMixin, records_to_json
from openai import OpenAI

class OrderService(AsyncMixin):
    async def __ainit__(self):
        self.supabase: AClient = await acreate_client(
            settings.supabase.supabase_url, settings.supabase.supabase_service_key, options=AsyncClientOptions(schema='myaso'))

        print(f"OrderService - Alibaba API Key: {settings.alibaba.alibaba_key[:10] if settings.alibaba.alibaba_key else 'EMPTY'}...")
        print(f"OrderService - Alibaba Base URL: {settings.alibaba.base_alibaba_url}")
        
        if not settings.alibaba.alibaba_key or not settings.alibaba.base_alibaba_url:
            raise ValueError(f"Alibaba settings are not properly configured. API Key: {'SET' if settings.alibaba.alibaba_key else 'EMPTY'}, Base URL: {settings.alibaba.base_alibaba_url}")
        
        self.embedder: OpenAI = OpenAI(
            api_key=settings.alibaba.alibaba_key,
            base_url=settings.alibaba.base_alibaba_url
        )

    async def get_all_products(self):
        result = await self.supabase.table('products').select('*').execute()
        return result.data if len(result.data) else []

    async def get_all_orders_by_client_phone(self, client_phone: str):
        result = await self.supabase.table('orders').select('*').eq('client_phone', client_phone).execute()
        return result.data if len(result.data) else []

    async def get_sys_variables(self):
        result = await self.supabase.table('system').select('*').execute()
        return result.data if len(result.data) else []

    async def find_products_by_query(self, query: str):
        print('find_products_by_query started')
        print(f"Embedder base_url: {self.embedder.base_url}")
        print(f"Embedder api_key: {self.embedder.api_key[:10]}...")
        
        conn = await asyncpg.connect(
                    dsn='postgres://postgres.your-tenant-id:N,$=~94SJRuWBU"h5kH;.2@51.250.35.208:5432/postgres'
                )
        completion = self.embedder.embeddings.create(model="text-embedding-v4", input=query)
        query_vector = completion.model_dump()['data'][0]['embedding']
        sql_request = f"""
        SELECT *
        FROM myaso.products
        ORDER BY embedding <-> '{query_vector}'
        LIMIT 10;
        """

        result = await conn.fetch(sql_request)
        json_result = records_to_json(result)

        print(json_result)
        for product in json_result:
            del product['embedding']
        return json_result if len(json_result) else []


