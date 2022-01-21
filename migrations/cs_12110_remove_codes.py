from collections import defaultdict
from catalog.db import get_profiles_collection, get_products_collection, init_mongo
from catalog.logging import setup_logging
from catalog.utils import get_now
from catalog.settings import SENTRY_DSN
import asyncio
import logging
import sentry_sdk


logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Start migration")
    counters = defaultdict(int)
    now = get_now().isoformat()
    profile_res = await get_profiles_collection().update_many(
        {},
        {
            "$unset": {"criteria.$[].code": ""},
            "$set": {"dateModified": now},
        },
    )
    product_res = await get_products_collection().update_many(
        {},
        {
            "$unset": {"requirementResponses.$[].id": ""},
            "$set": {"dateModified": now}
        },
    )
    counters.update({
        "total_profiles": profile_res.matched_count,
        "updated_profiles": profile_res.modified_count,
        "total_products": product_res.matched_count,
        "updated_products": product_res.modified_count
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
