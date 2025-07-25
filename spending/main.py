import asyncio

import logging
import bot, config, utils


logging.basicConfig(format=utils.log_format, level=utils.log_level)


async def main():
    await bot.run_bot(config.Config.Telegram.BOT_API_TOKEN)


if __name__ == '__main__':
    asyncio.run(main())
