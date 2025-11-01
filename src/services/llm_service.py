import os
import asyncio
import inspect
import asyncpg
from src.config.settings import settings
from tenacity import retry, stop_after_attempt, RetryError
from pydantic import BaseModel

# Set environment variables before importing OpenAI and Mirascope
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse.langfuse_public_key
os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse.langfuse_secret_key
os.environ["LANGFUSE_HOST"] = settings.langfuse.langfuse_host
os.environ["OPENAI_API_KEY"] = settings.openrouter.openrouter_api_key

from openai import OpenAI
from mirascope.core import (
    openai,
    BaseMessageParam,
    BaseDynamicConfig,
    Messages,
    BaseTool,
)
from mirascope.integrations.langfuse import with_langfuse
from supabase import create_client, Client, ClientOptions
from typing import List, Optional, Dict, Any
from pydantic import Field
import requests
import json


from src.services.history_service import HistoryService
from src.services.orders_service import OrderService

from src.utils import parse_sql_result, records_to_json


class SQLError(Exception):
    """Custom exception for SQL-related errors"""

    def __init__(self, message: str, sql_query: str = None, db_error: str = None):
        self.message = message
        self.sql_query = sql_query
        self.db_error = db_error
        super().__init__(message)


def collect_sql_errors(error_type):
    """
    Custom error collector for SQL errors, similar to Mirascope's collect_errors
    """

    def after_callback(retry_state):
        print(f"Retry attempt {retry_state.attempt_number} completed")

        if retry_state.outcome and retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            print(
                f"Attempt failed with exception: {type(exception).__name__}: {exception}"
            )

            if isinstance(exception, error_type):
                # Get the errors list from kwargs, or create a new one
                errors = retry_state.kwargs.get("errors", [])
                errors.append(exception)
                retry_state.kwargs["errors"] = errors
                print(f"Added error to list, total errors: {len(errors)}")
        else:
            print("Attempt succeeded")

        return retry_state

    return after_callback


supabase_client = create_client(
    settings.supabase.supabase_url,
    settings.supabase.supabase_service_key,
    options=ClientOptions(schema="myaso"),
)


class Product(BaseModel):
    title: str = Field(..., description="Title of the product")
    supplier_name: str = Field(..., description="Supplier name of the product")


class ShowProductPhotos(BaseTool):
    """Tool for showing photos of products."""

    products: List[Product] = Field(
        ..., description="List of products to search for photos"
    )
    phone_number: str = Field(
        ..., description="Phone number of the user requesting the photos"
    )

    def call(self) -> str:
        """
        Execute the tool to get photos of products.
        And send them with whatsapp api
        Returns:
            None
        """

        print("Uploading photos from Supabase...")
        print("products:", self.products)
        print("phone:", self.phone_number)

        has_photo = []
        no_photo = []

        for product in self.products:
            response = (
                supabase_client.table("products")
                .select("*")
                .eq("title", product.title)
                .eq("supplier_name", product.supplier_name)
                .execute()
            ).data
            print("response:", response)

            if len(response) == 0:
                continue

            if response[0].get("photo", None):
                print("Есть фото: ", product.title, response[0].get("photo", None))
                print(
                    {
                        "recipient": self.phone_number,
                        "image_url": response[0].get("photo", None),
                        "caption": product.title,
                    }
                )
                requests.post(
                    url="http://51.250.42.45:2026/sendImage",
                    json={
                        "recipient": self.phone_number,
                        "image_url": response[0].get("photo", None),
                        "caption": product.title,
                    },
                )

                has_photo.append(product.title)

            else:
                print("Нет фото: ", product.title)
                no_photo.append(product.title)

        # For testing purposes, return a success message
        return f"""
        Фотографии следующих товаров отправлены: {has_photo}.
        Нет фотографий следующих товаров: {no_photo}
        """


class EnhanceUserProductQuery(BaseTool):
    """Enhance user request by searching products in database with ebedding"""

    request: str = Field(..., description="user request about market assortiment")

    async def call(self) -> str:
        """
                Use this tool only if there is an explicit intention to find products in the current query or in connection with the immediate context, expressed through:

        ✅ Call the tool if:

        The query contains at least one search attribute.:
        • Type of meat (beef, pork, lamb, etc.)
        • Part of the carcass (tenderloin, shoulder, ribs)
        • Format (steak, minced meat, bones, chopped)
        • Weight, packaging, cooking method
        OR the request explicitly asks to show the assortment:
        • "What do you have?"
        • "Show all the meat"
        • "What steaks do you have?"
        OR the user asks for a recommendation with criteria:
        • "What do you recommend for grilling?" → there is a criterion "for grilling"
        • "What is suitable for soup?" → "for soup" criterion

        ❌ Do not call the tool if:
        Confirmation request/Rejection/response: "Yes", "No", "Ok", "Thank you"
        Service topics are discussed: delivery, payment, refund, work schedule
        The user clarifies the details of the already identified product:
        • "Does this steak have a photo?"
        • "How much does it weigh?"
        The query does not contain search attributes and does not ask for a general overview:
        • "Do you have good meat?"
        • "Do you recommend something?" (without specifying the purpose/criteria)
        The request consists only of polite or official words.: "Please", "May I?", "Hi"

        ⚠️ Critically important:

        Do not modify or enrich the user's request (for example, do not turn "Yes" into "Show products")
        Do not launch a search if the product is already known from the context — the tool is intended only for searching for new products.
        If in doubt, do not call the tool. It's better to skip than to trigger a false alarm.
        """

        print("Start to embedding user request: ", self.request)
        # Обогащаем контекстом запрос пользователя

        orders = await OrderService()
        products = await orders.find_products_by_query(self.request)

        print("products:", products)

        return f"""{products}"""


class LLMService:
    def __init__(self):
        print(f"API Key loaded: {settings.openrouter.openrouter_api_key[:10]}...")
        print(f"Base URL: {settings.openrouter.base_url}")
        print(f"Model ID: {settings.openrouter.model_id}")

        self.client: OpenAI = OpenAI(
            api_key=settings.openrouter.openrouter_api_key,
            base_url=settings.openrouter.base_url,
        )

        print(
            f"LLMService - Alibaba API Key: {settings.alibaba.alibaba_key[:10] if settings.alibaba.alibaba_key else 'EMPTY'}..."
        )
        print(f"LLMService - Alibaba Base URL: {settings.alibaba.base_alibaba_url}")

        self.embedder: OpenAI = OpenAI(
            api_key=settings.alibaba.alibaba_key,
            base_url=settings.alibaba.base_alibaba_url,
        )

        # Initialize Supabase client
        self.supabase: Client = create_client(
            settings.supabase.supabase_url, settings.supabase.supabase_service_key
        )

    async def infer(
        self,
        query: str,
        history: Optional[List[BaseMessageParam]] = None,
        session_id: Optional[str] = None,
    ):
        if history is None:
            history = []

        @with_langfuse()
        @openai.call(
            model=settings.openrouter.model_id,
            client=self.client,
            tools=[ShowProductPhotos, EnhanceUserProductQuery],
            call_params={"reasoning_effort": "medium"},
        )
        def _call(messages: List[BaseMessageParam]):
            return messages

        # Prepare messages
        messages: list[BaseMessageParam] = [
            *history,
        ]
        # Only add user message if query is not None or empty
        if query:
            messages.append(Messages.User(content=query))

        # Make the initial call
        response = _call(messages)

        # Handle tool calls if present
        if response.tool:
            # Extract tool call information before execution
            tool_call_info = {
                "name": response.tool.__class__.__name__,
                "arguments": response.tool.model_dump(),
            }

            # Execute the tool and get the result
            # Check if call method is async
            call_method = response.tool.call()
            if inspect.iscoroutine(call_method):
                tool_result = await call_method
            else:
                tool_result = call_method

            print(
                f"Tool {response.tool.__class__.__name__} executed with result: {tool_result}"
            )

            # Store tool information in the response for later access
            response._tool_call_info = tool_call_info
            response._tool_result = tool_result

            # Check if message.content is empty - only then make a second LLM call
            message_content = ""
            try:
                response_attr = getattr(response, "response", None)
                if response_attr is not None:
                    choices_attr = getattr(response_attr, "choices", None)
                    if choices_attr is not None:
                        message_content = choices_attr[0].message.content or ""
                else:
                    choices_attr = getattr(response, "choices", None)
                    if choices_attr is not None:
                        message_content = choices_attr[0].message.content or ""
            except Exception as e:
                print(f"Error extracting message content: {e}")
                message_content = ""

            if response.tool.__class__.__name__ == "EnhanceUserProductQuery":
                print("Called EnhanceUserProductQuery, making second LLM call...")
                print(f"Original query: {query}")
                print(f"Query type: {type(query)}")
                print(f"Query repr: {repr(query)}")

                # Collect tools and outputs for tool_message_params
                tools_and_outputs = [(response.tool, tool_result)]

                # Add the tool call and result to the conversation history
                messages.append(response.message_param)
                messages.extend(response.tool_message_params(tools_and_outputs))

                # Add user message to continue the conversation
                # Ensure query is properly encoded as UTF-8 string
                query_text = str(query).encode("utf-8").decode("utf-8") if query else ""
                final_message = (
                    f"На основе подобранных товаров, ответь на мой вопрос: {query_text}"
                )
                print(f"Final message to LLM: {final_message}")
                print(f"Final message repr: {repr(final_message)}")

                messages.append(Messages.User(content=final_message))

                # Make a second call with the tool result
                second_response = _call(messages)

                # Pass tool information to the second response
                second_response._tool_call_info = tool_call_info
                second_response._tool_result = tool_result

                return second_response

            # make second call if message content is empty
            if not message_content.strip():
                print("Message content is empty, making second LLM call...")

                # Collect tools and outputs for tool_message_params
                tools_and_outputs = [(response.tool, tool_result)]

                # Add the tool call and result to the conversation history
                messages.append(response.message_param)
                messages.extend(response.tool_message_params(tools_and_outputs))

                # Add user message to continue the conversation
                if response.tool.__class__.__name__ == "ShowProductPhotos":
                    messages.append(
                        Messages.User(content="Фотографии отправлены. Продолжай")
                    )

                else:
                    messages.append(Messages.User(content=tool_result))

                # Make a second call with the tool result
                second_response = _call(messages)

                # Pass tool information to the second response
                second_response._tool_call_info = tool_call_info
                second_response._tool_result = tool_result

                return second_response
            else:
                print("Message content is not empty, returning original response")
                return response

        return response

    async def get_sql_query(
        self,
        user_request: str,
        top_k_limit: int = None,
        client: dict = None,
        system_vars: dict = None,
        errors: list[SQLError] = [],
    ):

        @with_langfuse()
        @openai.call(
            model=settings.openrouter.model_id,
            client=self.client,
            call_params={"reasoning_effort": "medium"},
        )
        def _call(messages: List[BaseMessageParam]):
            return messages

        # Build error context if errors exist
        error_context = ""
        if errors:
            error_context = "\n\nPREVIOUS ERRORS TO AVOID:\n"
            for i, error in enumerate(errors, 1):
                error_context += f"Error {i}:\n"
                if error.sql_query:
                    error_context += f"- Failed SQL: {error.sql_query}\n"
                if error.db_error:
                    error_context += f"- Database Error: {error.db_error}\n"
                error_context += f"- Issue: {error.message}\n\n"
            error_context += "Please fix these issues in your new SQL query.\n"

        # Prepare messages
        messages: list[BaseMessageParam] = [
            Messages.System(
                content=f"""Given an input question, create a syntactically correct PostgreSQL query to
run to help find the answer. Unless the user specifies in his question a
specific number of examples they wish to obtain, always limit your query to
at most {top_k_limit} results. You can order the results by a relevant column to
return the most interesting examples in the database.


{f'CLIENT INFO: {client}' if client is not None else ''}
{f'SYSTEM VARIABLES: {system_vars if system_vars else "No system variables available"}' if system_vars is not None else ''}

Guidelines:
- ALWAYS USE SCHEMA "myaso" IN EACH QUERY. TABLES ARE NOT IN PUBLIC 
- Only use tables, columns, and relationships defined in the schema.
- Do not invent column or table names. If something is unclear, write a SQL comment.
- Use JOINs where necessary to combine data across tables.
- Use GROUP BY and aggregate functions when the question implies summarization.
- Always use LIMIT in queries requesting a preview or top-N results.
- Format queries cleanly with appropriate indentation.
- Never write DELETE, INSERT, UPDATE, DROP, or DDL statements.
- Prefer using table aliases (`c` for customers, `o` for orders) when dealing with multiple tables.
- ALWAYS PUT FINAL RESULT INSIDE ```sql <query> ``` block

Pay attention to use only the column names that you can see in the schema
description. Be careful to not query for columns that do not exist. Also,
pay attention to which column is in which table.

Only use the following tables:
--------------------------------------------------------------------------------------------------

Table clients:
Description: stores information about clients, including their contact details and business details

phone: type - text, required - true - Client's phone number
name: type - text, required - true - Client's name
created_at: type - timestampz, required - true, default - now() - Time when the client was added to the table
mode: type - text, required - false, default - autopilot
city: type - text, required - fasle - Client's city
business_area: type - text, required - false - Client's bussines area 
is_it_friend: type - boolean, required - false - Set true if the client is a friend
org_name - type - text, required - false - Client's organization name
UTC: type - int, required - false - Client's time zone in UTC format
sep_turnover: type - int, required - false 
oct_turnover: type - int, required - false

Foreign key relations: None

--------------------------------------------------------------------------------------------------

Table orders:
Description: The orders table tracks product orders placed by clients, linking each order to a client via phone number and storing key details such as product, quantity, pricing, and delivery destination.

id: type - UUID, primary - true
title: type - text, required - true - The ordered product's title
client_phone: type - text, required - true - Client's phone number. This client ordered the product
created_at: type - date, required - true - Order date
weight_kg: type - int, required - true - Product weight in the order
price_out: type - text, required - true - Order price
destination: type - text, required - true - Order delivery destination
price_out_kg: type - text, required - true - Product price (for one kilogram)

Foreign key relation to: myaso.clients
orders_client_phone_fkey: client_phone -> myaso.clients.phone

--------------------------------------------------------------------------------------------------

Table products:
Description: The products table stores information about available products, including their origin, pricing, packaging, delivery details, and logistical attributes, to support order preparation and client inquiries.

id: type - int, primary - true - ID product in database 
title: type - text, required - false - Product's title
from_region: type - text, required - false - Product's region of origin 
photo: type - text, required - false - Product photo's link
pricelist_date: type - date, required - false - Price at pricelist date
supplier_name: type - text, required - false - Supplier name
package_weight: type - float8, required - false - Weight of one product package
prepayment_1t: type - int8, required - false 
order_price_kg: type - float8, required - false - Price of one kilogram of the product  
min_order_weight_kg: type - int, required - false - Minimal allowed weight for order 
discount: type - text, required - false - Discount
ready_made: type - boolean, required - false - Is Ready-made food
package_type: type - text, required - false - Package type for product (box, package, pallet, etc)
cooled_or_frozen: type - text, required - false - Is this product cooled or frozen
product_in_package: type - text, required - false
embedding: type - vector, required - false - Embedding of product. Used in semantic search queries

Foreign key relations: None

--------------------------------------------------------------------------------------------------

Table price_history
Description: The price_history table tracks historical pricing data for products, recording the price of each product by supplier over time.

id: type - int8, primary - true
product: type - text, required - true - Product's title
date: type - date, required - true - Date
price: type - float, required - true - Product's price at the specified date
suplier_name: type - text, required - true - Supplier name

Foreign key relations: None

--------------------------------------------------------------------------------------------------

{error_context}
"""
            ),
            Messages.User(
                content="Translate the following user request into a SQL query: "
                + user_request
            ),
        ]

        # Make the initial call
        response = _call(messages)
        return response

    async def get_result_from_db_by_ai(
        self,
        user_request: str,
        top_k_limit: int = None,
        client: dict = None,
        system_vars: dict = None,
        errors: list[SQLError] = None,
    ):
        """
        Get SQL query result with automatic retry and error feedback loop.
        Returns {} if all retry attempts fail.
        """
        try:
            return await self._get_result_from_db_by_ai_with_retry(
                user_request=user_request,
                top_k_limit=top_k_limit,
                client=client,
                system_vars=system_vars,
                errors=errors or [],
            )
        except RetryError as e:
            print(
                f"All retry attempts failed after {e.last_attempt.attempt_number} attempts, returning empty dict"
            )
            return []

    @retry(stop=stop_after_attempt(3), after=collect_sql_errors(SQLError))
    async def _get_result_from_db_by_ai_with_retry(
        self,
        user_request: str,
        top_k_limit: int = None,
        client: dict = None,
        system_vars: dict = None,
        errors: list[SQLError] = None,
    ):
        """
        Internal method with retry logic.
        If SQL generation or execution fails, the error is collected and passed to the next attempt.
        """
        try:
            # Get errors from retry state if available (from previous attempts)
            current_errors = errors or []

            print(
                f"Starting SQL query attempt with {len(current_errors)} previous errors"
            )

            # Generate SQL query with error context from previous attempts
            response = await self.get_sql_query(
                user_request, top_k_limit, client, system_vars, current_errors
            )

            # Extract content from response
            content = ""
            try:
                response_attr = getattr(response, "response", None)
                if response_attr is not None:
                    choices_attr = getattr(response_attr, "choices", None)
                    if choices_attr is not None:
                        content = choices_attr[0].message.content
                    else:
                        content = str(response_attr)
                else:
                    choices_attr = getattr(response, "choices", None)
                    if choices_attr is not None:
                        content = choices_attr[0].message.content
                    else:
                        content = str(response)
            except Exception as e:
                content = f"Error extracting content: {str(e)}"

            # Parse SQL from response
            try:
                sql_request = parse_sql_result(content)
            except ValueError as e:
                raise SQLError(
                    message=f"Failed to parse SQL from AI response: {str(e)}",
                    sql_query=None,
                    db_error=None,
                )

            # Security check for dangerous operations
            if (
                "insert" in sql_request.lower()
                or "update" in sql_request.lower()
                or "delete" in sql_request.lower()
            ):
                raise SQLError(
                    message="AI attempted to generate dangerous SQL operation (INSERT/UPDATE/DELETE)",
                    sql_query=sql_request,
                    db_error=None,
                )

            print(f"Generated SQL: {sql_request}")

            # Execute SQL query
            conn = None
            try:
                conn = await asyncpg.connect(
                    dsn='postgres://postgres.your-tenant-id:N,$=~94SJRuWBU"h5kH;.2@51.250.35.208:5432/postgres'
                )
                result = await conn.fetch(sql_request)

                print(f"Query result: {result}")

                # Convert Record objects to JSON-compatible dictionaries
                json_result = records_to_json(result)

                print(f"JSON result: {json_result}")

                if json_result:
                    for product in json_result:
                        del product["embedding"]

                return json_result

            except Exception as db_error:
                # Database execution error - create SQLError with context
                error_message = str(db_error)

                raise SQLError(
                    message=f"{error_message}",
                    sql_query=sql_request,
                    db_error=error_message,
                )
            finally:
                if conn:
                    await conn.close()

        except SQLError:
            # Re-raise SQLError as-is for retry mechanism
            raise
        except Exception as e:
            # Convert any other exception to SQLError
            raise SQLError(
                message=f"Unexpected error: {str(e)}", sql_query=None, db_error=str(e)
            )

    async def embedd_products(self):
        products = (supabase_client.table("products").select("*").execute()).data

        for product in products:
            print(product)
            print()
            text_description = f"""Товар {product['title']} из {product['from_region']} поставщиком которого - компания {product['supplier_name']}, является {product['cooled_or_frozen']} продуктом. Упаковывается в {product['package_type']}. Фасовка продукта {product['product_in_package']}. {"Товар является полуфабрикатом" if product['ready_made'] else "Товар не является полуфабрикатом"}. Скидка на товар - {product['discount']}"""
            print()
            print(text_description)
            print()
            completion = self.embedder.embeddings.create(
                model="text-embedding-v4", input=text_description
            )
            vector = completion.model_dump()["data"][0]["embedding"]
            supabase_client.table("products").upsert(
                {**product, "embedding": vector}
            ).execute()


llm = LLMService()
