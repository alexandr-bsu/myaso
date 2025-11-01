#!/usr/bin/env python3
"""
Тест для проверки условного вызова LLM после tool call
"""

import asyncio
import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.llm_service import llm

async def test_conditional_llm_call():
    """Тестируем условный вызов LLM после tool call"""
    
    # Тест 1: Запрос, который должен вызвать инструмент ShowProductPhotos
    query1 = "Покажи фотографии филе грудок кур от поставщика Приосколье для клиента +79246506083"
    
    print("=== ТЕСТ 1: Обычный запрос с tool call ===")
    print("Запрос:", query1)
    print("-" * 50)
    
    try:
        response1 = await llm.infer(query=query1, history=[])
        
        print("Получен ответ:")
        
        # Проверяем наличие tool call информации
        tool_call_info = getattr(response1, "_tool_call_info", None)
        tool_result = getattr(response1, "_tool_result", None)
        
        if tool_call_info:
            print("✓ Tool Call Info найден:", tool_call_info["name"])
        
        if tool_result:
            print("✓ Tool Result найден:", str(tool_result)[:100] + "...")
            
        # Проверяем основной content
        try:
            response_attr = getattr(response1, "response", None)
            if response_attr is not None:
                choices_attr = getattr(response_attr, "choices", None)
                if choices_attr is not None:
                    content = choices_attr[0].message.content
                    print("LLM Content:", content if content else "[ПУСТОЙ]")
            else:
                choices_attr = getattr(response1, "choices", None)
                if choices_attr is not None:
                    content = choices_attr[0].message.content
                    print("LLM Content:", content if content else "[ПУСТОЙ]")
        except Exception as e:
            print("Error extracting content:", e)
            
        print("=" * 50)
        
    except Exception as e:
        print(f"Ошибка в тесте 1: {e}")
        import traceback
        traceback.print_exc()

    # Тест 2: Запрос, который может дать пустой content (для демонстрации логики)
    print("\n=== ТЕСТ 2: Простой запрос без tool call ===")
    query2 = "Привет, как дела?"
    print("Запрос:", query2)
    print("-" * 50)
    
    try:
        response2 = await llm.infer(query=query2, history=[])
        
        print("Получен ответ:")
        
        # Проверяем наличие tool call информации
        tool_call_info = getattr(response2, "_tool_call_info", None)
        tool_result = getattr(response2, "_tool_result", None)
        
        if tool_call_info:
            print("✓ Tool Call Info найден:", tool_call_info["name"])
        else:
            print("✗ Tool Call Info не найден (ожидаемо)")
        
        if tool_result:
            print("✓ Tool Result найден:", str(tool_result)[:100] + "...")
        else:
            print("✗ Tool Result не найден (ожидаемо)")
            
        # Проверяем основной content
        try:
            response_attr = getattr(response2, "response", None)
            if response_attr is not None:
                choices_attr = getattr(response_attr, "choices", None)
                if choices_attr is not None:
                    content = choices_attr[0].message.content
                    print("LLM Content:", content[:100] + "..." if content and len(content) > 100 else content)
            else:
                choices_attr = getattr(response2, "choices", None)
                if choices_attr is not None:
                    content = choices_attr[0].message.content
                    print("LLM Content:", content[:100] + "..." if content and len(content) > 100 else content)
        except Exception as e:
            print("Error extracting content:", e)
            
        print("=" * 50)
        print("Все тесты завершены!")
        
    except Exception as e:
        print(f"Ошибка в тесте 2: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conditional_llm_call())