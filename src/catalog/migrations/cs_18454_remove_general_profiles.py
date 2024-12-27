import asyncio
import logging
from pymongo import UpdateOne

import sentry_sdk

from catalog.db import get_profiles_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.migrations.cs_15202_migrate_requirement_expected_value_to_values import bulk_update
from catalog.models.profile import ProfileStatus
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")
    bulk = []
    counter = 0
    async with transaction_context_manager() as session:
        profiles_collection = get_profiles_collection()
        async for profile in profiles_collection.find(
            {"status": "general"},
            session=session
        ):
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": profile["_id"]},
                    update={"$set": {"status": ProfileStatus.hidden, "dateModified": now}}
                )
            )
            counter += 1
            if bulk and len(bulk) % 500 == 0:
                await bulk_update(profiles_collection, bulk, session, counter, migrated_obj="profiles")
                bulk = []

        if bulk:
            await bulk_update(profiles_collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} records of migrated profiles")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
