import argparse
import asyncio
import logging

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_products_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate_categories(category_id):
    logger.info("Start category migration")
    category_collection = get_category_collection()
    async with transaction_context_manager() as session:
        now = get_now().isoformat()
        await category_collection.update_one(
            {"_id": category_id},
            {
                "$set": {
                    "dateModified": now,
                    "title": "Насоси та компресори",
                    "description": "Насоси та компресори",
                }
            },
            session=session,
        )
    logger.info("Finished. Updated category.")


async def migrate_products(category_id, old_category_id):
    logger.info("Start products migration")
    counter = 0
    bulk = []
    product_collection = get_products_collection()
    async for product in product_collection.find({"relatedCategory": old_category_id}):
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": product["_id"]},
                update={
                    "$set": {
                        "dateModified": now,
                        "relatedCategory": category_id,
                    }
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(
                    product_collection, bulk, session, counter, migrated_obj="products"
                )
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(
                product_collection, bulk, session, counter, migrated_obj="products"
            )

    logger.info(f"Finished. Processed {counter} updated products")


async def migrate(args):
    await migrate_categories(args.id)
    await migrate_products(args.id, args.old_id)
    logger.info("Successfully migrated")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--id",
        type=str,
        help="Compressors category id",
        required=True,
    )
    parser.add_argument(
        "--old_id",
        type=str,
        help="Old compressors category id",
        required=True,
    )
    return parser.parse_args()


def main():
    """
    PYTHONPATH=/app python catalog/migrations/cs_20828_patch_compressor_category.py --id "<compressor category id>" --old_id "<old compressor id>"
    """
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate(parse_args()))


if __name__ == "__main__":
    main()
