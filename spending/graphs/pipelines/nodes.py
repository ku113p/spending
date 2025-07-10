from typing import Any, TypedDict

import db, utils

logger = utils.create_logger()


class InsertToDb(TypedDict):
    data: dict
    inserted_id: Any


async def save_to_db(state: InsertToDb):
    inserted_id = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.CREATE),
        {"doc": state['data']}
    )

    return {"inserted_id": inserted_id}


class PublishToRedis(TypedDict):
    channel_name: str
    task_id: Any
    received: bool


async def redis_publish(state: PublishToRedis):
    channel_name = state['channel_name']
    task_id = state['task_id']

    received: int = await utils.publish_message(channel_name, task_id)

    return {"received": bool(received)}
