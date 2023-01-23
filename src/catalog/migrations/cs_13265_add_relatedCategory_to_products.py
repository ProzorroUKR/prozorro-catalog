from dataclasses import dataclass
import asyncio
import logging

from pymongo.errors import PyMongoError
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_profiles: int = 0
    total_products: int = 0
    updated_products: int = 0
    skipped_products: int = 0

    def __post_init__(self):
        self.total_products = self.total_products or (
            self.updated_products +
            self.skipped_products
        )

    def __add__(self, other):
        return Counters(
            self.total_profiles + other.total_profiles,
            self.total_products + other.total_products,
            self.updated_products + other.updated_products,
            self.skipped_products + other.skipped_products,
        )


async def migrate():
    logger.info("Start migration")
    counters = Counters()
    async for profile in get_profiles_collection().find({}, projection={"_id": 1, "relatedCategory": 1}):
        try:
            stats = await migrate_products(profile)
        except PyMongoError as e:
            logger.warning(f"Handled mongo error: {e}")
            stats = Counters()
        counters.total_profiles += 1

        # update global counters
        counters += stats
        if counters.total_profiles % 500 == 0:
            logger.info(f"Stats: {counters}")
    logger.info(f"Finished. Stats: {counters}")
    return counters


async def migrate_products(profile: dict):
    counters = Counters()

    products_collection = get_products_collection()
    async with transaction_context_manager() as session:
        now = get_now().isoformat()
        bulk = []
        query = {"relatedProfiles": {"$in": [profile["_id"]]}}
        async for p in products_collection.find(query, session=session):
            bulk.append(
                UpdateOne(
                    filter={"_id": p["_id"]},
                    update={"$set": {"relatedCategory": profile["relatedCategory"], "dateModified": now}}
                )
            )
            counters.updated_products += 1

        if bulk:
            bulk_len = len(bulk)
            result = await products_collection.bulk_write(bulk, session=session)
            if result.modified_count != len(bulk):
                logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
            counters.skipped_products += bulk_len - result.modified_count
    return counters


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
