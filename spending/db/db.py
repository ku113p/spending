import enum
from dataclasses import dataclass
from typing import Any, Callable, Self

from pydantic import BaseModel


class OperationType(enum.Enum):
    INIT = enum.auto()
    CREATE = enum.auto()
    LIST = enum.auto()
    DELETE = enum.auto()
    GET = enum.auto()
    UPDATE = enum.auto()


class DbType(enum.Enum):
    MONGO = enum.auto()


@dataclass(unsafe_hash=True)
class DbOperation:
    db: DbType
    operation: OperationType
    
    @classmethod
    def mongo(cls, op: OperationType) -> Self:
        return cls(db=DbType.MONGO, operation=op)


OperationHandler = Callable[[BaseModel], Any]
OperationSchema = type[BaseModel]


@dataclass
class OperationInstructions:
    schema_cls: OperationSchema | None
    handler: OperationHandler


operation_registry: dict[DbOperation, OperationInstructions] = {}


def register_operation(db_op: DbOperation, schema_cls: type[OperationSchema] | None) -> Callable[[OperationHandler], OperationHandler]:
    def decorator(handler: OperationHandler) -> OperationHandler:
        instructions = OperationInstructions(schema_cls=schema_cls, handler=handler)
        operation_registry[db_op] = instructions
        return handler
    return decorator


async def run_operation(db_op: DbOperation, params: dict):
    try:
        instructions = operation_registry[db_op]
    except KeyError:
        raise ValueError(f"No handler registered for {db_op}")
    
    return await (
        instructions.handler()
        if instructions.schema_cls is None
        else instructions.handler(instructions.schema_cls(**params))
    )
