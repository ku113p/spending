from collections.abc import AsyncIterator
import csv
from dataclasses import asdict, dataclass
import enum
import datetime

from traitlets import Any

from . import day, month


class ExportType(enum.Enum):
    DAY = "day"
    MONTH = "month"


@dataclass
class ExportConfig:
    type: ExportType
    dt: datetime.datetime
    filepath: str
    
    async def export(self) -> int | None:
        rows = self._get_rows()
        first_row = await anext(rows, None)
        if first_row is None:
            return  # Nothing to write

        headers = list(first_row.keys())

        with open(self.filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow(first_row)

            counter = 1
            async for row in rows:
                counter += 1
                writer.writerow(row)
                
        return counter
    
    async def _get_rows(self) -> AsyncIterator[Any]:
        rows_generatit = {
            ExportType.DAY: day.collect,
            ExportType.MONTH: month.collect_monthly
        }[self.type](self.dt)
        
        async for row in rows_generatit:
            yield asdict(row)
