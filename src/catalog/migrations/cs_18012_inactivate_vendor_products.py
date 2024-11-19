import asyncio
import logging
from datetime import datetime

import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.models.product import ProductStatus
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")
    bulk = []
    counter = 0
    async with transaction_context_manager() as session:
        collection = get_products_collection()

        async for obj in collection.find(
            {"vendor": {"$exists": True}},
            projection={"dateCreated": 1, "status": 1},
        ):
            counter += 1
            now = get_now()
            product_year = datetime.fromisoformat(obj["dateCreated"]).year
            update_data = {
                "expirationDate": datetime(
                    year=product_year, month=12, day=31, hour=23, minute=59, second=59, tzinfo=now.tzinfo,
                ).isoformat(),
                "dateModified": now.isoformat(),
            }
            if obj["status"] == ProductStatus.hidden or product_year < now.year:
                update_data["status"] = ProductStatus.inactive
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": update_data},
                )
            )

            if bulk and len(bulk) % 500 == 0:
                await bulk_update(collection, bulk, session, counter, migrated_obj="products")
                bulk = []

        if bulk:
            await bulk_update(collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} records of migrated products")


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
