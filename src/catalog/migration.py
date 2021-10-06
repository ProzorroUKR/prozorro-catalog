from pymongo.errors import DuplicateKeyError, PyMongoError
from catalog.settings import CATALOG_DATA
from catalog.db import (
    get_category_collection,
    get_profiles_collection,
    get_products_collection,
    get_offers_collection,
)
import aiofiles
import aiofiles.os
import asyncio
import os.path
import logging
from json import loads as json_loads

logger = logging.getLogger(__name__)


async def import_data_job(app):
    if CATALOG_DATA:
        args = (
            ("category", get_category_collection()),
            ("profile", get_profiles_collection()),
            ("product", get_products_collection()),
            ("offer", get_offers_collection()),
        )
        await asyncio.gather(*(
            import_items(item_name, col)
            for item_name, col in args
        ))
    else:
        logger.info("Import job is skipped")


async def import_items(name, collection):
    path = os.path.join(CATALOG_DATA, name)
    count = 0
    for file_name in os.listdir(path):
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            async with aiofiles.open(file_path, mode='r') as f:
                contents = await f.read()
            json = json_loads(contents)
            # {"data": {..item data..}, "access": {}}
            data = json["data"]
            data["access"] = json["access"]
            data["_id"] = data.pop("id")
            count += await insert_object(collection, data)
    logger.info(f"Imported {count} of {name} objects")


async def insert_object(collection, data):
    while True:
        try:
            await collection.insert_one(data)
        except DuplicateKeyError:
            logger.warning(f"Document with id {data['_id']} already exists")
            return 0
        except PyMongoError as e:
            logger.exception(e)
            await asyncio.sleep(2)
        else:
            return 1


if __name__ == "__main__":
    from catalog.logging import setup_logging
    from catalog.settings import SENTRY_DSN
    from catalog.db import init_mongo
    import sentry_sdk

    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo(None))
    loop.run_until_complete(import_data_job())


