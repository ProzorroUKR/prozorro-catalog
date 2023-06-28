from dataclasses import dataclass
from datetime import timedelta
import asyncio
import logging

from pymongo.errors import PyMongoError
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_category_collection, get_profiles_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_categories: int = 0
    total_profiles: int = 0
    updated_profiles: int = 0
    skipped_profiles: int = 0

    def __post_init__(self):
        self.total_profiles = self.total_profiles or (
            self.updated_profiles +
            self.skipped_profiles
        )

    def __add__(self, other):
        return Counters(
            self.total_categories + other.total_categories,
            self.total_profiles + other.total_profiles,
            self.updated_profiles + other.updated_profiles,
            self.skipped_profiles + other.skipped_profiles,
        )


async def migrate():
    logger.info("Start migration")
    counters = Counters()
    async for category in get_category_collection().find({}, projection={"_id": 1, "agreementID": 1}):
        try:
            stats = await migrate_profiles(category)
        except PyMongoError as e:
            logger.warning(f"Handled mongo error: {e}")
            stats = Counters()
        counters.total_categories += 1

        # update global counters
        counters += stats
        if counters.total_profiles % 500 == 0:
            logger.info(f"Stats: {counters}")
    logger.info(f"Finished. Stats: {counters}")
    return counters


async def migrate_profiles(category: dict):
    counters = Counters()

    profiles_collection = get_profiles_collection()
    async with transaction_context_manager() as session:
        bulk = []
        async for p in profiles_collection.find({"relatedCategory": category["_id"]}, session=session):
            bulk.append(
                UpdateOne(
                    filter={"_id": p["_id"]},
                    update={"$set": {
                        "agreementID": category["agreementID"], "dateModified": get_now().isoformat()}
                    }
                )
            )
            counters.updated_profiles += 1

        if bulk:
            bulk_len = len(bulk)
            result = await profiles_collection.bulk_write(bulk, session=session)
            if result.modified_count != len(bulk):
                logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
            counters.skipped_profiles += bulk_len - result.modified_count
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
