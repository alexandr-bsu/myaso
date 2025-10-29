from src.main import app
from uvicorn import run

run(app)

# from src.services.orders_service import OrderService
# import asyncio


# async def main():
    # orders = OrderService()
    # embedder = llm_service.embedder

    # completion = embedder.embeddings.create(model="text-embedding-v4", input="Что у вас есть из продукции корал?")

    # print(completion.model_dump_json())

    # await llm_service.embedd_products()

    # print(await orders.find_products_by_query("Что у вас есть из продукции корал?"))
#     response = await llm_service.get_result_from_db_by_ai("Покажи все товары, цена которых упала более чем на 10% по сравнению с предыдущей неделей. В таблице могут не оказаться записи именно с такими датами, ищи ближайшие даты, но разница между сегодняшним числом (ИСПОЛЬЗУЙ ФУНКЦИЮ NOW() ДЛЯ ТОГО ЧТОБЫ ПОЛУЧИТЬ СЕГОДНЯШНЕЕ ЧИСЛО) и датой в таблице должна быть минимальной, но не меньше 7 дней")
#     print(response)


# if __name__ == "__main__":
    # asyncio.run(main())
