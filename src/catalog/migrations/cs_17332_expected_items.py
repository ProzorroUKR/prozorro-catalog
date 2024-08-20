import asyncio
import logging
import sentry_sdk
from uuid import uuid4
from copy import deepcopy

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


CATEGORY_ID = "99999999-919912-02426097"


def update_criteria(criteria):
    changed = False

    for c in criteria:
        for rg in c.get("requirementGroups", ""):
            for req in rg.get("requirements", ""):
                if req.get("expectedValues"):
                    req["expectedMinItems"] = 1
                    if req.get("expectedMaxItems") and req.get("expectedMaxItems") != 1:
                        req.pop("expectedMaxItems", None)
                    changed = True
    return changed


async def migrate():
    logger.info("Start migration")

    bulk = []
    counter = 0
    collection = get_category_collection()
    async with transaction_context_manager() as session:
        async for obj in collection.find(
            {"_id": {"$ne": CATEGORY_ID}, "status": {"$ne": "hidden"}},
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
                await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} records of migrated categories")
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
