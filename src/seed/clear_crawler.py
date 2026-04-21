import asyncio
import logging
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from catalog.logging import setup_logging
from catalog.settings import DB_NAME, MONGODB_URI

logger = logging.getLogger(__name__)
    
async def clear():
    logger.info("init mongodb instance")
    loop = asyncio.get_event_loop()
    conn = AsyncIOMotorClient(MONGODB_URI, io_loop=loop)
    CRAWLER_DB_NAME = 'crawler-' + DB_NAME
    result = await conn[CRAWLER_DB_NAME]['prozorro-crawler-state'].delete_many({})
    print(f'Deleted: {result.deleted_count}')



if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(clear())
    except Exception:
        logger.exception("Clear crawler state failed")
        sys.exit(1)