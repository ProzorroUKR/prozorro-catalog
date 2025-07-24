import asyncio

import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


CLASSIFICATION_IDS = ["34210000-2", "34610000-6", "43120000-0", "43210000-8"]


async def migrate():
    logger.info("Start products migration for renaming field `schema` to `scheme`")
    counter = 0
    bulk = []
    products_collection = get_products_collection()
    async for product in products_collection.find(
            {"classification.id": {"$in": CLASSIFICATION_IDS}, "classification.schema": {"$exists": True}},
            {"classification": 1},
    ):
        bulk.append(
            UpdateOne(
                filter={"_id": product["_id"]},
                update={
                    "$rename": {"classification.schema": "classification.scheme"},
                    "$set": {"dateModified": get_now().isoformat()},
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} updated products' fields.")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
