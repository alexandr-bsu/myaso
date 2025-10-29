# from src.main import app
# from uvicorn import run

# run(app)

from src.services.llm_service import LLMService
import asyncio



async def main():
    llm_service = LLMService()
    response = await llm_service.get_result_from_db_by_ai("Покажи все товары, цена которых упала более чем на 10% по сравнению с предыдущей неделей. В таблице могут не оказаться записи именно с такими датами, ищи ближайшие даты, но разница между сегодняшним числом (ИСПОЛЬЗУЙ ФУНКЦИЮ NOW() ДЛЯ ТОГО ЧТОБЫ ПОЛУЧИТЬ СЕГОДНЯШНЕЕ ЧИСЛО) и датой в таблице должна быть минимальной, но не меньше 7 дней")
    print(response)


if __name__ == '__main__':
    asyncio.run(main())
