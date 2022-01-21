import asyncio
import logging
from collections import defaultdict
from datetime import timedelta

from pymongo import UpdateOne
import sentry_sdk

from catalog.db import get_profiles_collection, get_products_collection, init_mongo, transaction_context_manager
from catalog.logging import setup_logging
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN


logger = logging.getLogger(__name__)


async def update_many_with_different_dateModified(collection, update_req, session=None, time_diff=1):
    bulk = []
    now = get_now()
    async for doc in collection.find(projection="_id"):

        bulk.append(
            UpdateOne(
                filter={"_id": doc["_id"]},
                update={
                    **update_req,
                    "$set": {"dateModified": now.isoformat()},
                },
            )
        )
        now -= timedelta(seconds=time_diff)

    if bulk:
        result = await collection.bulk_write(bulk, session=session)
        if result.modified_count != len(bulk):
            logger.error(f"Unexpected modified_count: {result.modified_count}; expected {len(bulk)}")
        return result.modified_count


async def migrate():
    logger.info("Start migration")
    counters = defaultdict(int)

    profile_collection = get_profiles_collection()
    products_collection = get_products_collection()

    updated_profiles = await update_many_with_different_dateModified(
        profile_collection,
        {"$unset": {"criteria.$[].code": ""}},
    )

    updated_products = await update_many_with_different_dateModified(
        products_collection,
        {"$unset": {"requirementResponses.$[].id": ""}},
    )

    counters.update({
        "updated_profiles": updated_profiles,
        "updated_products": updated_products,
    })
    logger.info(f"Finished. Stats: {dict(counters)}")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
