import argparse
import asyncio
import logging
from datetime import datetime

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate_products(old_expiration_date, new_expiration_date):
    logger.info("Start products migration")
    counter = 0
    bulk = []
    products_collection = get_products_collection()
    async for product in products_collection.find(
        {
            "vendor": {"$exists": True},
            "status": "active",
            "expirationDate": old_expiration_date,
        }
    ):
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": product["_id"]},
                update={
                    "$set": {
                        "dateModified": now,
                        "expirationDate": new_expiration_date,
                    }
                },
            )
        )
        counter += 1

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(
                    products_collection, bulk, session, counter, migrated_obj="products"
                )
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(
                products_collection, bulk, session, counter, migrated_obj="products"
            )

    logger.info(f"Finished. Processed {counter} updated products")
    logger.info("Successfully migrated")


async def migrate(args):
    # check if old_expiration_date and new_expiration_date are in isoformat
    datetime.fromisoformat(args.old_expiration_date)
    datetime.fromisoformat(args.new_expiration_date)

    await migrate_products(args.old_expiration_date, args.new_expiration_date)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--old_expiration_date",
        type=str,
        help="Old expiration date",
        required=True,
    )
    parser.add_argument(
        "--new_expiration_date",
        type=str,
        help="New expiration date",
        required=True,
    )
    return parser.parse_args()


def main():
    """
    OLD_DATE=<old expiration date>
    NEW_DATE=<new expiration date>
    PYTHONPATH=/app python catalog/migrations/cs_20838_change_expiration_date.py --old_expiration_date="${OLD_DATE}" --new_expiration_date="${NEW_DATE}"
    """
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate(parse_args()))


if __name__ == "__main__":
    main()
