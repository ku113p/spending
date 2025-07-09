import enum

import aiohttp

from config import Config


class ToTextStrategy(enum.Enum):
    MICROSERVICE = enum.auto()

    async def to_text(self, photo_filepath: str) -> str:
        method = {
            ToTextStrategy.MICROSERVICE: photo_to_text
        }[self]
        result = await method(photo_filepath)
        return result


async def photo_to_text(photo_filepath: str) -> str:
    async with aiohttp.ClientSession() as session:
        with open(photo_filepath, "rb") as file:
            files = {"file": file}
            async with session.post(Config.TO_TEXT_URL, data=files) as resp:
                if resp.status != 200:
                    raise Exception("failed extract text from photo_to_text")
                
                payload = await resp.json()
                return payload["text"]
