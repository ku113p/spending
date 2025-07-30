import datetime
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass
from typing import AsyncIterator

import db


@dataclass
class MonthlySummaryRow:
    category: str
    total_price: float


async def collect_monthly(dt: datetime.datetime) -> AsyncIterator[MonthlySummaryRow]:
    start_of_month = dt.replace(day=1)
    start_of_next_month = dt + relativedelta(months=1)

    pipeline = [
        {
            "$match": {
                "receipt.created_at": {
                    "$gte": start_of_month,
                    "$lt": start_of_next_month
                }
            }
        },
        {
            "$unwind": "$receipt.products"
        },
        {
            "$group": {
                "_id": "$receipt.products.category",
                "total_price": {"$sum": "$receipt.products.price"}
            }
        },
        {
            "$sort": {"total_price": -1}
        },
        {
            "$project": {
                "_id": 0,
                "category": "$_id",
                "total_price": 1
            }
        }
    ]

    raw_rows: AsyncIterator[dict] = await db.run_operation(
        db_op=db.DbOperation.mongo(db.OperationType.AGGREGATE),
        params={"pipeline": pipeline}
    )
    
    async for raw in raw_rows:
        yield MonthlySummaryRow(**raw)
