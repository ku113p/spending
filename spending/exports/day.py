import datetime
from dataclasses import dataclass
from typing import AsyncIterator

import db


@dataclass
class DayItemRow:
    name: str
    price: float
    shop: str
    invoice_number: str


async def collect(dt: datetime.datetime) -> AsyncIterator[DayItemRow]:
    start_date = dt
    end_date = dt + datetime.timedelta(days=1)

    pipeline = [
        {
            "$match": {
                "receipt.created_at": {
                    "$gte": start_date,
                    "$lt": end_date
                }
            }
        },
        {
            "$unwind": "$receipt.products"
        },
        {
            "$sort": {
                "receipt.number": 1,
                "receipt.products.name.normalized": 1
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": "$receipt.products.name.normalized",
                "price": "$receipt.products.price",
                "shop": "$receipt.shop.name.normalized",
                "invoice_number": "$receipt.number"
            }
        }
    ]
    
    raw_rows: AsyncIterator[dict] = await db.run_operation(
        db_op=db.DbOperation.mongo(db.OperationType.AGGREGATE),
        params={"pipeline": pipeline}
    )
    
    async for raw in raw_rows:
        yield DayItemRow(**raw)
