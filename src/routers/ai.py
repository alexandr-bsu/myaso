from fastapi import APIRouter, BackgroundTasks
from src.schemas import (
    ConversationHistoryMessage,
    LLMRequest,
    InitConverastionRequest,
    UserMessageRequest,
    ResetConversationRequest,
    Profile,
)
from src.services.llm_service import llm, ShowProductPhotos
from src.services.history_service import HistoryService
from src.services.profile_service import ProfileService
from src.services.orders_service import OrderService
from src.utils import transorm_history_to_llm_format, remove_markdown_symbols
import re
import requests
import json
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/ai")


async def init_conversation_background(request: InitConverastionRequest):
    hs = await HistoryService()
    # print('HS', await hs.get_history(request.client_phone))

    try:
        # Get AI response first
        ai_response = await ask(
            LLMRequest(client_phone=request.client_phone, topic=request.topic)
        )

        # Add system instructions to history if present
        # if ai_response.get('instructions_with_context'):
        #     await hs.add_message_to_conversation_history(ConversationHistoryMessage(client_phone=request.client_phone, message=ai_response['instructions_with_context'][0]['content'], role=ai_response['instructions_with_context'][0]['role']))

        # Add the RAG context (full_prompt) to history
        # This ensures the context is saved to Supabase database
        if ai_response.get("rag_context"):
            await hs.add_message_to_conversation_history(
                ConversationHistoryMessage(
                    client_phone=request.client_phone,
                    message=ai_response["rag_context"],
                    role="user",
                )
            )

        # Add tool calls to history if present
        if ai_response.get("tool_calls"):
            for tool_call in ai_response["tool_calls"]:
                # Check if this is a tool call with name and arguments or detected from history
                if "name" in tool_call and "arguments" in tool_call:
                    tool_message = f"Tool call: {tool_call['name']} with args: {json.dumps(tool_call['arguments'])}"
                else:
                    # This is a tool call detected from history
                    tool_message = tool_call.get("detected_from_history", "Tool call")
                await hs.add_message_to_conversation_history(
                    ConversationHistoryMessage(
                        client_phone=request.client_phone,
                        message=tool_message,
                        role="tool",
                    )
                )

        # Add tool responses to history if present
        if ai_response.get("tool_responses"):
            for tool_response in ai_response["tool_responses"]:
                await hs.add_message_to_conversation_history(
                    ConversationHistoryMessage(
                        client_phone=request.client_phone,
                        message=tool_response,
                        role="tool",
                    )
                )

        # Add assistant response to history
        await hs.add_message_to_conversation_history(
            ConversationHistoryMessage(
                client_phone=request.client_phone,
                message=ai_response["content"],
                role="assistant",
            )
        )

        # TODO: Перевести контент в формат whatsapp
        # print('ai_response init_conversation_background', remove_markdown_symbols(ai_response['content']))
        # requests.post(
        #     "http://51.250.42.45:2026/send-message",
        #     json={
        #         "recipient": request.client_phone,
        #         "message": remove_markdown_symbols(ai_response["content"]),
        #     },
        # )
        return {"content": remove_markdown_symbols(ai_response["content"])}
        # return {"succes": True}

    except Exception as e:
        # requests.post(
        #     "http://51.250.42.45:2026/send-message",
        #     json={
        #         "recipient": request.client_phone,
        #         "message": "Произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
        #     },
        # )
        print(f"ERROR in init_conversation_background: {e}")
        import traceback

        traceback.print_exc()
        # return {"succes": False}
        return {
            "content": "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
        }


async def process_conversation_background(request: UserMessageRequest):
    hs = await HistoryService()

    # Обогащаем контекстом запрос пользователя
    orders = await OrderService()
    products = await orders.find_products_by_query(request.message)

    enhaced_prompt = f"""
    =================================================
    Подходящие под текущий вопрос/запрос товары:
    {products}
    =================================================

    На основе этих товаров, ответь на сообщение: {request.message}
    """
    try:
        # Get AI response first
        ai_response = await ask(
            LLMRequest(client_phone=request.client_phone, prompt=enhaced_prompt)
        )
        print("ai_response process_conversation_background", request.message)

        # Add user message to history
        await hs.add_message_to_conversation_history(
            ConversationHistoryMessage(
                client_phone=request.client_phone, message=enhaced_prompt, role="user"
            )
        )

        # Add tool calls to history if present
        if ai_response.get("tool_calls"):
            for tool_call in ai_response["tool_calls"]:
                # Check if this is a tool call with name and arguments or detected from history
                if "name" in tool_call and "arguments" in tool_call:
                    tool_message = f"Tool call: {tool_call['name']} with args: {json.dumps(tool_call['arguments'])}"
                else:
                    # This is a tool call detected from history
                    tool_message = tool_call.get("detected_from_history", "Tool call")
                await hs.add_message_to_conversation_history(
                    ConversationHistoryMessage(
                        client_phone=request.client_phone,
                        message=tool_message,
                        role="tool",
                    )
                )

        # Add tool responses to history if present
        if ai_response.get("tool_responses"):
            for tool_response in ai_response["tool_responses"]:
                await hs.add_message_to_conversation_history(
                    ConversationHistoryMessage(
                        client_phone=request.client_phone,
                        message=tool_response,
                        role="tool",
                    )
                )

        # Add assistant response to history
        await hs.add_message_to_conversation_history(
            ConversationHistoryMessage(
                client_phone=request.client_phone,
                message=ai_response["content"],
                role="assistant",
            )
        )

        # TODO: Перевести контент в формат whatsapp
        # print('ai_response process_conversation_background', remove_markdown_symbols(ai_response['content']))
        # requests.post(
        #     "http://51.250.42.45:2026/send-message",
        #     json={
        #         "recipient": request.client_phone,
        #         "message": remove_markdown_symbols(ai_response["content"]),
        #     },
        # )
        # return {"succes": True}
        return {"content": remove_markdown_symbols(ai_response["content"])}

    except Exception as e:
        # requests.post(
        #     "http://51.250.42.45:2026/send-message",
        #     json={
        #         "recipient": request.client_phone,
        #         "message": "Произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
        #     },
        # )
        print(f"ERROR in process_conversation_background: {e}")
        import traceback

        traceback.print_exc()
        # return {"succes": False}
        return {
            "content": "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
        }


# TODO: Сделать сброс истории и инициализировать новый диалог (ktopравить сообщение клиенту)
async def reset_conversation_background(request: ResetConversationRequest):
    hs = await HistoryService()
    await hs.delete_conversation_history(client_phone=request.client_phone)
    return {"succes": True}


@router.delete("/resetConversation", status_code=200)
async def reset_conversation(
    request: ResetConversationRequest, background_tasks: BackgroundTasks
):
    background_tasks.add_task(reset_conversation_background, request)
    return {"succes": True}


@router.post("/initConversation", status_code=200)
async def init_conversation(
    request: InitConverastionRequest, background_tasks: BackgroundTasks
):
    # background_tasks.add_task(init_conversation_background, request)
    # return {"succes": True}
    return await init_conversation_background(request)


@router.post("/processConversation", status_code=200)
async def process_conversation(
    request: UserMessageRequest, background_tasks: BackgroundTasks
):
    # background_tasks.add_task(process_conversation_background, request)
    # return {"succes": True}
    return await process_conversation_background(request)


@router.get("/getProfile", status_code=200)
async def get_profile(request: Profile):
    profile_service = await ProfileService()
    profile = await profile_service.get_profile(client_phone=request.client_phone)
    return profile


async def ask(request: LLMRequest) -> Dict[str, Any]:
    history_service = await HistoryService()

    message_history = await transorm_history_to_llm_format(
        await history_service.get_history(client_phone=request.client_phone)
    )
    system_instructions = await history_service.get_instructions(
        topic=request.topic if request.topic is not None else "Продать"
    )

    rag_context = None  # Initialize RAG context variable

    # инициируем общение если не указан prompt
    if not request.prompt:
        if system_instructions:
            profile_service = await ProfileService()
            profile = await profile_service.get_profile(
                client_phone=request.client_phone
            )

            order_service = await OrderService()
            orders = await order_service.get_all_orders_by_client_phone(
                client_phone=request.client_phone
            )
            products = await order_service.get_all_products()
            sys_variables = await order_service.get_sys_variables()

            products = await llm.get_result_from_db_by_ai(
                user_request=(
                    await history_service.get_instructions(
                        topic="Получить товары при инициализации диалога"
                    )
                ).get("prompt", ""),
                top_k_limit=10,
                client=profile,
                system_vars=sys_variables,
            )

            # Handle the case where system_instructions might not be a dict
            if isinstance(system_instructions, dict):
                prompt_content = (
                    system_instructions.get("prompt", "") if system_instructions else ""
                )
            else:
                prompt_content = str(system_instructions)

            full_prompt = f"""
            Профиль клиента: {profile}
            ===============================================
            Системные переменные: {sys_variables}
            ===============================================
            Предыдущие заказы клиента: {orders}
            ===============================================
            Подходящие товары: {products}
            ===============================================
            {prompt_content}
            """

            # Store the RAG context to be saved later
            rag_context = full_prompt

            message_history.append({"role": "user", "content": full_prompt})

    # Call LLM
    # Note: The LLM service will automatically add the query as a user message,
    # so we don't need to add it to message_history ourselves
    response = await llm.infer(query=request.prompt or "", history=message_history)

    # Extract content from response
    # Handle both direct response and response with tool calls
    content = ""
    try:
        # Check if this is a tool call response - use the tool result as content
        tool_result = getattr(response, "_tool_result", None)
        if tool_result is not None:
            # For tool calls, use the original LLM content + tool result
            response_attr = getattr(response, "response", None)
            if response_attr is not None:
                choices_attr = getattr(response_attr, "choices", None)
                if choices_attr is not None:
                    llm_content = choices_attr[0].message.content
                else:
                    llm_content = ""
            else:
                choices_attr = getattr(response, "choices", None)
                if choices_attr is not None:
                    llm_content = choices_attr[0].message.content
                else:
                    llm_content = ""

            # Combine LLM content with tool result
            content = llm_content if llm_content else str(tool_result)
        else:
            # Regular response without tool calls
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

    # Постобработка ответа ИИ
    content = re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()

    # Check for tool calls
    tool_calls: List[Dict[str, Any]] = []
    tool_responses: List[str] = []

    try:
        # Check if response has tool information attached by the LLM service
        tool_call_info = getattr(response, "_tool_call_info", None)
        if tool_call_info is not None:
            tool_calls.append(tool_call_info)

        tool_result = getattr(response, "_tool_result", None)
        if tool_result is not None:
            tool_responses.append(str(tool_result))
    except Exception as e:
        tool_responses.append(f"Error processing tools: {str(e)}")

    # Handle system instructions
    instructions_context = []
    if not request.prompt and system_instructions:
        if isinstance(system_instructions, dict) and "prompt" in system_instructions:
            instructions_context = [
                {"role": "user", "content": system_instructions["prompt"]}
            ]

    # Return the response with RAG context included
    result = {
        "content": content,
        "instructions_with_context": instructions_context,
        "tool_calls": tool_calls,
        "tool_responses": tool_responses,
    }

    # Include RAG context if it was generated
    if rag_context:
        result["rag_context"] = rag_context

    return result
