from typing import Callable
import uuid

from langchain_core.runnables import Runnable

import db, utils
from config import Config
from graphs.pipelines import image_to_normailized_receipt, nodes
from graphs.pipelines.photo_to_receipt import local_ocr, openai_only

from integrations.to_text import ToTextStrategy


logger = utils.create_logger(__name__)


@utils.async_timing(logger)
async def extract_text():
    text = await ToTextStrategy.MICROSERVICE.to_text(Config.TestData.IMAGE_FP)
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
    return await test_receipt_graph(local_ocr.create)


async def test_receipt_graph(builder: Callable[[], Runnable]):
    graph = builder()

    try:
        lf_handler = [utils.get_langfuse_handler()]
    except Exception as e:
        lf_handler = []
        logger.error(f"Failed get_langfuse_handler: {e}")

    receipt = await graph.ainvoke(
        {"image_fp": Config.TestData.IMAGE_FP},
        config={"callbacks": [*lf_handler]}
    )

    logger.info(f"receipt:\n{receipt}")

    return receipt


@utils.async_timing(logger)
async def test_img_to_schema():
    return await test_receipt_graph(openai_only.create)


@utils.async_timing(logger)
async def test_img_to_norm():
    return await test_receipt_graph(image_to_normailized_receipt.create)


@utils.async_timing(logger)
async def test_save_and_receive():
    import asyncio
    from typing import Any, TypedDict
    from langgraph.graph import START, END, StateGraph

    class TestState(TypedDict):
        data: dict
        inserted_id: Any

        channel_name: str
        task_id: Any
        received: bool

    
    graph_builder = StateGraph(TestState)
    graph_builder.add_node("save_to_db", nodes.save_to_db)
    graph_builder.add_node("redis_publish", nodes.redis_publish)
    graph_builder.add_edge(START, "save_to_db")
    graph_builder.add_edge("save_to_db", "redis_publish")
    graph_builder.add_edge("redis_publish", END)
    graph = graph_builder.compile()

    channel_name = "test_chan"
    task_id = uuid.uuid4()
    data = {"id_": task_id, "foo": "bar"}
    state = {"data": data, "channel_name": channel_name, "task_id": task_id}

    async def callback(data):
        logger.info(f"cb: {type(data).__name__}({data})")

    subscriber_task = asyncio.create_task(utils.subscribe_to_channel(channel_name, callback))
    result = await graph.ainvoke(state)
    logger.info(f"result of ainvoke: {result}")

    await asyncio.sleep(1)
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        logger.info("Subscriber task cancelled.")


async def check():
    # await extract_text()
    # await test_db()
    # await test_agent()
    # await test_img_to_schema()
    # await test_img_to_norm()
    await test_save_and_receive()
