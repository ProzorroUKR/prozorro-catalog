import argparse
import asyncio
import logging

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import get_category_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate_categories(category_ids):
    logger.info("Start categories migration")
    counter = 0
    bulk = []
    category_collection = get_category_collection()
    async for category in category_collection.find({"_id": {"$in": category_ids}}):
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": category["_id"]},
                update={
                    "$set": {
                        "dateModified": now,
                        "status": "hidden",
                    }
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(
                    category_collection,
                    bulk,
                    session,
                    counter,
                    migrated_obj="categories",
                )
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(
                category_collection, bulk, session, counter, migrated_obj="categories"
            )

    logger.info(f"Finished. Processed {counter} updated categories")
    logger.info("Successfully migrated")


async def migrate(args):
    await migrate_categories(args.id)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--id",
        type=str,
        nargs="+",
        help="Category id",
        required=True,
    )
    return parser.parse_args()


def main():
    """
    PYTHONPATH=/app python catalog/migrations/cs_20828_hide_category.py --id "<category 1 id>" "<category 2 id>"
    """
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate(parse_args()))


if __name__ == "__main__":
    main()
