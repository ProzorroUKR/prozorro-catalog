import asyncio
import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


def update_criteria(criteria):
    changed = False

    for c in criteria:
        for rg in c.get("requirementGroups", []):
            for req in rg.get("requirements", []):
                if req.get("expectedValues") and req.get("dataType") == "string" and not req.get("expectedMinItems"):
                    req["expectedMinItems"] = 1
                    changed = True
    return changed


async def migrate():
    logger.info("Start migration")

    bulk = []
    counter = 0
    collection = get_profiles_collection()
    async with transaction_context_manager() as session:
        async for obj in collection.find(
            {"criteria": {"$exists": True}},
            projection={"_id": 1, "criteria": 1}
        ):
            if update_criteria(obj["criteria"]):
                counter += 1

                now = get_now().isoformat()
                bulk.append(
                    UpdateOne(
                        filter={"_id": obj["_id"]},
                        update={"$set": {
                            "criteria": obj["criteria"],
                            "dateModified": now}
                        }
                    )
                )

            if bulk and len(bulk) % 500 == 0:
                await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} records of migrated profiles")
    logger.info("Successfully migrated")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
