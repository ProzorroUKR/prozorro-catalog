import asyncio
import csv

import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
    get_products_collection,
    get_profiles_collection,
)
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)

MZU_CATEGORIES_FIELDS_MAPPING = {
    (
        "33140000-236865-42574629",
        "33140000-899035-425746299",
        "33140000-226343-42574629",
        "33140000-073089-42574629",
        "33141120-133022-42574629",
    ): {
        "classification.id": "33160000-9",
        "classification.description": "Устаткування для операційних блоків",
    },
    (
        "33140000-455036-42574629",
        "33140000-420119-42574629",
        "33140000-073030-42574629",
    ): {
        "classification.id": "33171000-9",
        "classification.description": "Анестезійні та реанімаційні інструменти",
    },
    (
        "33140000-344973-42574629",
        "33190000-370694-42574629",
        "33190000-376066-42574629",
        "33190000-360669-42574629",
        "33190000-761376-42574629",
        "33190000-458330-42574629",
        "33190000-150732-425746299",
        "33190000-977417-42574629",
    ): {
        "classification.id": "33141000-0",
        "classification.description": "Медичні матеріали нехімічні та гематологічні одноразового застосування",
    },
    (
        "33140000-852237-42574629",
        "33140000-135632-42574629",
    ): {
        "classification.id": "33120000-7",
        "classification.description": "Системи реєстрації медичної інформації та дослідне обладнання",
    },
    (
        "33140000-303561-425746299",
        "33140000-073025-42574629",
        "33140000-904348-42574629",
    ): {
        "classification.id": "33180000-5",
        "classification.description": "Апаратура для підтримування фізіологічних функцій організму",
    },
    (
        "33190000-740938-42574629",
        "33190000-255387-425746299",
    ): {
        "classification.id": "33141300-3",
        "classification.description": "Прилади для венепункції та забору крові",
    },
    (
        "33190000-357864-42574629",
        "33190000-678665-42574629",
        "33190000-181818-42574629",
        "33190000-151515-42574629",
        "33190000-770066-42574629",
        "33190000-616161-42574629",
        "33190000-333333-42574629",
        "33192500-231224-42574629",
        "33190000-161616-42574629",
    ): {
        "classification.id": "33141600-6",
        "classification.description": "Контейнери та пакети для забору матеріалу для аналізів, дренажі та комплекти",
    },
}


async def migrate_categories():
    logger.info("Start MZU categories' fields migration")
    counter = 0
    bulk = []
    category_collection = get_category_collection()

    for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
        async for category in category_collection.find(
            {"_id": {"$in": list(category_ids)}},
        ):
            update_fields = {
                "classification.id": update_data["classification.id"],
                "classification.description": update_data["classification.description"],
                "dateModified": get_now().isoformat()
            }
            bulk.append(
                UpdateOne(
                    filter={"_id": category["_id"]},
                    update={"$set": update_fields},
                )
            )
            counter += 1

            if bulk and len(bulk) % 500 == 0:
                async with transaction_context_manager() as session:
                    await bulk_update(category_collection, bulk, session, counter, migrated_obj="categories")
                bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(category_collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} updated categories' fields.")


async def migrate_profiles():
    obj_collection = get_profiles_collection()
    logger.info("Start localized profiles migration")
    counter = 0
    bulk = []

    with open('/tmp/cs_20827_mzu_profiles.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["id", "relatedCategory", "title", "classification.id", "classification.description"], extrasaction="ignore")
        writer.writeheader()
        for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
            async for obj in obj_collection.find(
                {"relatedCategory": {"$in": list(category_ids)}},
            ):
                update_fields = {
                    "classification.id": update_data["classification.id"],
                    "classification.description": update_data["classification.description"],
                    "dateModified": get_now().isoformat()
                }
                bulk.append(
                    UpdateOne(
                        filter={"_id": obj["_id"]},
                        update={"$set": update_fields},
                    )
                )
                profile_data = {
                    "id": obj["_id"],
                    "relatedCategory": obj["relatedCategory"],
                    "title": obj["title"],
                    "classification.id": update_data["classification.id"],
                    "classification.description": update_data["classification.description"],
                }
                writer.writerow(profile_data)
                counter += 1

                if bulk and len(bulk) % 500 == 0:
                    async with transaction_context_manager() as session:
                        await bulk_update(obj_collection, bulk, session, counter, migrated_obj="profiles")
                    bulk = []

        if bulk:
            async with transaction_context_manager() as session:
                await bulk_update(obj_collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} updated profiles")
    logger.info("Successfully migrated")


async def migrate_products():
    obj_collection = get_products_collection()
    logger.info("Start localized products migration")
    counter = 0
    bulk = []

    for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
        async for obj in obj_collection.find(
            {"relatedCategory": {"$in": list(category_ids)}},
        ):
            update_fields = {
                "classification.id": update_data["classification.id"],
                "classification.description": update_data["classification.description"],
                "dateModified": get_now().isoformat()
            }
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": update_fields},
                )
            )
            counter += 1

            if bulk and len(bulk) % 500 == 0:
                async with transaction_context_manager() as session:
                    await bulk_update(obj_collection, bulk, session, counter, migrated_obj="products")
                bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(obj_collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} updated products")
    logger.info("Successfully migrated")


async def migrate():
    await migrate_categories()
    await migrate_profiles()
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