import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from pymongo import UpdateOne
import sentry_sdk

from catalog.db import get_vendor_collection, init_mongo
from catalog.logging import setup_logging
from catalog.models.vendor import VendorStatus
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN


logger = logging.getLogger(__name__)


@dataclass
class Counters:
    total_vendors: int = 0
    succeeded_vendors: int = 0
    skipped_vendors: int = 0


async def run_task():
    vendor_collection = get_vendor_collection()
    counters = Counters()
    bulk = []

    async for vendor in vendor_collection.find(
            {"status": VendorStatus.banned, "bans": {"$exists": True}},
            projection={"bans": 1},
            no_cursor_timeout=True,
    ):
        for ban in vendor["bans"]:
            if datetime.fromisoformat(ban["dueDate"]) > get_now():
                break
        else:
            bulk.append(
                UpdateOne(
                    filter={"_id": vendor["_id"]},
                    update={
                        "$set": {"status": VendorStatus.active, "dateModified": get_now().isoformat()},
                    },
                )
            )
            counters.total_vendors += 1

    if bulk:
        result = await vendor_collection.bulk_write(bulk)
        bulk_len = len(bulk)
        if result.modified_count != bulk_len:
            logger.error(f"Unexpected modified_count: {result.modified_count}; expected {bulk_len}")
        counters.succeeded_vendors = result.modified_count
        counters.skipped_vendors = counters.total_vendors - result.modified_count

    logger.info(f"Finished. Stats: {counters}")
    return counters


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(run_task())


if __name__ == '__main__':
    main()
