from src.main import app
from uvicorn import run

run(app)

# import asyncio
# from src.services.orders_service import OrderService

# async def main():
#     orders = await OrderService()
#     orders = list(filter(lambda p: p['id'] in [1,2,3],await orders.get_all_products()))

#     result = []

#     for order in orders:
#         o = order.copy()
#         if(order['rice_in_kg'] <= 100){
#             o['price_in_kg'] =  order['price_in_kg']
#         }
    
#     print(orders)
# asyncio.run(main())
