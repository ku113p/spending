import asyncio

import db, utils
from graphs.graphs import to_receipt
from config import Config
from to_text import ToTextStrategy


logger = utils.create_logger(__name__)


@utils.async_timing(logger)
async def extract_text():
    text = await ToTextStrategy.MICROSERVICE.to_text("/home/ku113p/Downloads/photo_2025-07-03_00-41-32.jpg")
    logger.info(f"text:\n{text}")
    return text


@utils.async_timing(logger)
async def test_db():
    await db.run_operation(db.DbOperation.mongo(op=db.OperationType.INIT), {})
    
    create_result = await db.run_operation(db.DbOperation.mongo(op=db.OperationType.CREATE), {"doc": {"foo": "bar"}})
    logger.info(f"created = {create_result}")
    
    docs = await db.run_operation(db.DbOperation.mongo(op=db.OperationType.LIST), {"filter": {}})
    ind = -1
    async for d in docs:
        ind += 1
        logger.info(f"{ind=} | {d}")
    
    delete_result = await db.run_operation(db.DbOperation.mongo(op=db.OperationType.DELETE), {"filter": {}})
    logger.info(f"deleted: {delete_result}")


@utils.async_timing(logger)
async def test_agent():
    response = await to_receipt(text=Config.TestData.RECEIPT)

    logger.info(f"response:\n{response}")

    return response


async def main():
    # await extract_text()
    # await test_db()
    await test_agent()


asyncio.run(main())
