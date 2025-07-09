import asyncio

import use_cases


async def main():
    await use_cases.check()


asyncio.run(main())
