from typing import Callable
import uuid

from langchain_core.runnables import Runnable

import db, utils
from config import Config
from graphs.pipelines import correct_receipt, image_to_normailized_receipt, nodes
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


async def test_extract_receipt_and_save():
    from typing import TypedDict
    from langgraph.graph import START, END, StateGraph
    from graphs.agents import schemas

    class State(TypedDict):
        image_fp: str
        normalized_receipt: schemas.NormalizedReceipt
        data: dict
        inserted_id: uuid.UUID
    
    async def prep_for_save(state: State):
        norm_rec = state['normalized_receipt']
        return {"data": {"_id": uuid.uuid4(), "receipt": norm_rec.model_dump()}}

    norm_rec_subgraph = image_to_normailized_receipt.create()
    graph_builder = StateGraph(State)
    graph_builder.add_node("norm_rec_subgraph", norm_rec_subgraph)
    graph_builder.add_node("prep_for_save", prep_for_save)
    graph_builder.add_node("save_to_db", nodes.save_to_db)
    graph_builder.add_edge(START, "norm_rec_subgraph")
    graph_builder.add_edge("norm_rec_subgraph", "prep_for_save")
    graph_builder.add_edge("prep_for_save", "save_to_db")
    graph_builder.add_edge("save_to_db", END)
    graph = graph_builder.compile()

    result = await graph.ainvoke({"image_fp": Config.TestData.IMAGE_FP})
    logger.info(f"{result=}")


async def test_correct_receipt():
    task_id = uuid.UUID("4b75c511-52d6-49e0-9224-16a58b7f21bb")
    # user_input = "Pistachio price was 83"
    user_input = "Date to 06/14/2025"

    graph = correct_receipt.create()
    result = await graph.ainvoke({"task_id": task_id, "user_input": user_input})
    logger.info(f"{result=}")


async def check():
    # await extract_text()
    # await test_db()
    # await test_agent()
    # await test_img_to_schema()
    # await test_img_to_norm()
    # await test_save_and_receive()
    # await test_extract_receipt_and_save()
    await test_correct_receipt()
