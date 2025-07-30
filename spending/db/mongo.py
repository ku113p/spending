from contextlib import asynccontextmanager
from pydantic import BaseModel
from pymongo import AsyncMongoClient
from pymongo.asynchronous.cursor import AsyncCursor
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
from typing import Any, AsyncGenerator, AsyncIterable

import utils

from .db import DbOperation, DbType, OperationType, register_operation
from config import Config


logger = utils.create_logger(__name__)


@asynccontextmanager
async def _get_client() -> AsyncGenerator[AsyncMongoClient, None]:
    async with AsyncMongoClient(Config.Mongo.URI, uuidRepresentation="standard") as client:
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
async def create_document(params: CreateParams) -> Any:
    async with _get_collection() as collection:
        result = await collection.insert_one(params.doc)
        return result.inserted_id


class FilterParams(BaseModel):
    filter: dict
    limit: int | None = None
    skip: int | None = None
    sort: list[tuple[str, int]] | None = None

    def mongo_query(self, collection: AsyncCollection) -> AsyncCursor:
        query = collection.find(self.filter)
        if self.limit is not None:
            query = query.limit(self.limit)
        if self.skip is not None:
            query = query.skip(self.skip)
        if self.sort is not None:
            query = query.sort(self.sort)
        return query


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.LIST), schema_cls=FilterParams)
async def list_documents(params: FilterParams) -> AsyncIterable[dict]:
    async def doc_generator():
        async with _get_collection() as collection:
            async for doc in params.mongo_query(collection):
                yield doc

    return doc_generator()


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.COUNT), schema_cls=FilterParams)
async def count_documents(params: FilterParams) -> int:
    async with _get_collection() as collection:
        result = await collection.count_documents(params.filter)
        return result


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.DELETE), schema_cls=FilterParams)
async def delete_documents(params: FilterParams) -> int:
    documents_to_delete: list = await list_documents(params)
    ids = [doc["_id"] async for doc in documents_to_delete]
    async with _get_collection() as collection:
        result = await collection.delete_many({'_id': {'$in': ids}})
        return result.deleted_count


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.GET), schema_cls=FilterParams)
async def get_documet(params: FilterParams) -> dict | None:
    async with _get_collection() as collection:
        result: dict = await collection.find_one(params.filter)
        return result


class UpdateParams(BaseModel):
    filter: dict
    update: dict


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.UPDATE), schema_cls=UpdateParams)
async def update_one(params: UpdateParams) -> bool:
    async with _get_collection() as collection:
        result = await collection.update_one(
            filter=params.filter,
            update=params.update
        )
        return result.modified_count > 0


class AggregateParams(BaseModel):
    pipeline: list[dict[str, Any]]


@register_operation(db_op=DbOperation(db=DbType.MONGO, operation=OperationType.AGGREGATE), schema_cls=AggregateParams)
async def aggregate(params: AggregateParams) -> AsyncIterable[dict]:
    async def doc_generator():
        async with _get_collection() as collection:
            async for doc in await collection.aggregate(params.pipeline):
                yield doc

    return doc_generator()
