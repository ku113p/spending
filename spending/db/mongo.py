from contextlib import asynccontextmanager
from pydantic import BaseModel
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
from typing import AsyncGenerator, AsyncIterable

import utils

from .db import DbOperation, DbType, OperationType, register_operation
from config import Config


logger = utils.create_logger(__name__)


@asynccontextmanager
async def _get_client() -> AsyncGenerator[AsyncMongoClient, None]:
    async with AsyncMongoClient(Config.Mongo.URI) as client:
        yield client


@asynccontextmanager
async def _get_db() -> AsyncGenerator[AsyncDatabase, None]:
    async with _get_client() as client:
        yield client[Config.Mongo.DB_NAME]


@asynccontextmanager
async def _get_collection() -> AsyncGenerator[AsyncCollection, None]:
    async with _get_db() as db:
        yield db[Config.Mongo.COLLECTION_NAME]


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.INIT), schema_cls=None)
async def init_db():
    async with _get_db() as db:
        collections = await db.list_collection_names()
        if Config.Mongo.COLLECTION_NAME not in collections:
            await db.create_collection(Config.Mongo.COLLECTION_NAME)
            logger.info(f"Collection '{Config.Mongo.COLLECTION_NAME}' created.")
        else:
            logger.info(f"Collection '{Config.Mongo.COLLECTION_NAME}' already exists.")


class CreateParams(BaseModel):
    doc: dict


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.CREATE), schema_cls=CreateParams)
async def create_document(params: CreateParams) -> str:
    async with _get_collection() as collection:
        result = await collection.insert_one(params.doc)
        return str(result.inserted_id)


class FilterParams(BaseModel):
    filter: dict


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.LIST), schema_cls=FilterParams)
async def list_documents(params: FilterParams) -> AsyncIterable[dict]:
    async def doc_generator():
        async with _get_collection() as collection:
            async for doc in collection.find(params.filter):
                yield doc

    return doc_generator()


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.DELETE), schema_cls=FilterParams)
async def delete_documents(params: FilterParams) -> int:
    async with _get_collection() as collection:
        result = await collection.delete_many(params.filter)
        return result.deleted_count
