import asyncio

import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_products_collection,
)
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


LOCALIZATION_CATEGORIES_FIELDS_MAPPING = {
    ("9d5e7400fab3461a9d918d008609fcba", "fe6ea96017d14c5d9921940e79ec727e", "9a9a600adff5470c97aa485cc5e0819f"): {
        "classification.id": "18410000-6",
        "classification.description": "Спеціальний одяг",
    },
    ("26fc5bdbc8514715be712d7a17502dc5", "895e8d69188d47d4b2ca146e9737de8c", "a2afab475a664240a9a0b9b219021bdf"): {
        "classification.id": "18440000-5",
        "classification.description": "Головні убори",
    },
    ("fed5bbe29e364262bd7b87fa3d70d1bb", "8d88fbe12f0e4c22bb76d9f0b14c2a5b", "36bbf7baf5184bcaa77fe5367777081a"): {
        "classification.id": "31500000-1",
        "classification.description": "Освітлювальна техніка",
    },
    ("f94e0b4bf87346f9b80a25bd33eb2090", "c9f0c451690e45ef9cc9ad5525fbab5e", "ac25ea12a2724af68dcf9675fd390b1e"): {
        "classification.id": "39511000-7",
        "classification.description": "Ковдри",
    },
    ("03942ac1d48f473b909a81eb0114bc12", "1b844f8e9c0a408bb74a8c867750b40f", "d7fa81b8dfbe4ede99e1cf91aa2f46a8"): {
        "classification.id": "34928000-8",
        "classification.description": "Облаштування для доріг",
    },
    ("64053e34eb654f77a4502727d2791484", "3d7e83b4885e49e0b1d0b1f1e75007c9", "9ce4f8b01ce948c99ec29d0560ef907b"): {
        "classification.id": "34996000-5",
        "classification.description": "Регулювальне, запобіжне чи сигнальне дорожнє обладнання",
    },
    ("95aa601b17ce4d86a5403ae8aa5e47b5", "7e969806129c48a5a91d51418a03ef3e", "c31a9345bc6644db8e2ef5a690478b01"): {
        "classification.id": "18100000-0",
        "classification.description": "Формений одяг, спеціальний робочий одяг та аксесуари",
    }
}


async def migrate_products():
    logger.info("Start localized products migration")
    counter = 0
    bulk = []
    products_collection = get_products_collection()

    for category_ids, update_data in LOCALIZATION_CATEGORIES_FIELDS_MAPPING.items():
        async for product in products_collection.find(
            {"relatedCategory": {"$in": category_ids}},
        ):
            update_data["dateModified"] = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": product["_id"]},
                    update={"$set": update_data},
                )
            )
            counter += 1

            if bulk and len(bulk) % 500 == 0:
                async with transaction_context_manager() as session:
                    await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")
                bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(products_collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} updated products")
    logger.info("Successfully migrated")


async def migrate():
    await migrate_products()


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
