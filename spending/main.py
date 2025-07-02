import asyncio, time

from to_text import ToTextStrategy


async def main():
    t = time.time()
    result = await ToTextStrategy.MICROSERVICE.to_text("/home/ku113p/Downloads/photo_2025-07-03_00-41-32.jpg")
    print(result)
    print(time.time() - t)


asyncio.run(main())
