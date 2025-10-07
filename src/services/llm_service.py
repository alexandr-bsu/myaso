from openai import OpenAI
from mirascope.core import openai, BaseMessageParam, BaseDynamicConfig, Messages, BaseTool
from src.config.settings import settings
from mirascope.integrations.langfuse import with_langfuse
from supabase import create_client, Client, ClientOptions
from typing import List, Optional, Dict, Any
from pydantic import Field
import requests
import json

import os
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse.langfuse_public_key
os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse.langfuse_secret_key
os.environ["LANGFUSE_HOST"] = settings.langfuse.langfuse_host


supabase_client = create_client(
    settings.supabase.supabase_url,
    settings.supabase.supabase_service_key,
    options=ClientOptions(schema='myaso')
    )


class ShowProductPhotos(BaseTool):
    """Tool for showing photos of products."""

    product_names: List[str] = Field(
        ...,
        description="List of product names to search for photos"
    )
    phone_number: str = Field(
        ...,
        description="Phone number of the user requesting the photos"
    )

    def call(self) -> str:
        """
        Execute the tool to get photos of products.
        And send them with whatsapp api
        Returns:
            None
        """

        print("Uploading photos from Supabase...")
        print("product_names:", ', '.join(self.product_names))
        print("phone:", self.phone_number)

        for product_name in self.product_names:
            response = (supabase_client.table('products').select(
                '*').eq('title', product_name).execute()).data
            print("response:", response)

            if len(response) == 0:
                continue

            if response[0].get('photo', None):
                print("Есть фото: ", product_name, response[0].get('photo', None))
                print({'recipient': self.phone_number, 'image_url': response[0].get('photo', None), 'caption': product_name})
                requests.post(url='http://51.250.42.45:2026/sendImage', json={'recipient': self.phone_number, 'image_url': response[0].get('photo', None), 'caption': product_name})

            else:
                print("Нет фото: ", product_name)


        # For testing purposes, return a success message
        return "Фотографии успешно отправлены."


class LLMService:
    def __init__(self):
        self.client: OpenAI = OpenAI(
            api_key=settings.openrouter.openrouter_api_key, base_url=settings.openrouter.base_url)
        # Initialize Supabase client
        self.supabase: Client = create_client(
            settings.supabase.supabase_url,
            settings.supabase.supabase_service_key
        )

    async def infer(self, query: str, history: Optional[List[BaseMessageParam]] = None, session_id: Optional[str] = None):
        if history is None:
            history = []

        @with_langfuse()
        @openai.call(
            model=settings.openrouter.model_id,
            client=self.client,
            tools=[ShowProductPhotos],
            call_params={
                'reasoning_effort': 'medium',
                'max_tokens': 1800*3
            }
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
                'name': response.tool.__class__.__name__,
                'arguments': response.tool.model_dump()
            }

            # Execute the tool and get the result
            tool_result = response.tool.call()
            print(
                f"Tool {response.tool.__class__.__name__} executed with result: {tool_result}")

            # Store tool information in the response for later access
            response._tool_call_info = tool_call_info
            response._tool_result = tool_result

            # Collect tools and outputs for tool_message_params
            tools_and_outputs = [(response.tool, tool_result)]

            # Add the tool call and result to the conversation history
            # Add the assistant's tool call message
            messages.append(response.message_param)
            messages.extend(response.tool_message_params(
                tools_and_outputs))  # Add tool results

            # Make a second call with the tool result
            messages.append(Messages.User(
                content="Фотографии товара успешно отправлены. Продолжи диалог"))
            second_response = _call(messages)

            # Pass tool information to the second response
            second_response._tool_call_info = tool_call_info
            second_response._tool_result = tool_result

            return second_response

        return response


llm = LLMService()
