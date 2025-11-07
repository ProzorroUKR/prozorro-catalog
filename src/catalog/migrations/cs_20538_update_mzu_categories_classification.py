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
        "33140000-627164-42574629",
        "33141000-000003-42574629",
        "33140000-377843-42574629",
        "33140000-461635-42574629",
        "33140000-839586-425746299",
        "33140000-779063-425746299",
        "33140000-708001-42574629",
        "33140000-301839-42574629",
        "33140000-263254-42574629",
        "33140000-136296-42574629",
        "33140000-633652-42574629",
        "33140000-838383-42574629",
        "33140000-969696-42574629",
        "33140000-073017-42574629",
        "33140000-073018-42574629",
        "33140000-073020-42574629",
        "33140000-073021-42574629",
        "33140000-073022-42574629",
        "33140000-073023-42574629",
        "33140000-364467-42574629",
        "33140000-523496-42574629",
        "33140000-135633-42574629",
        "33140000-135636-42574629",
        "33140000-073031-42574629",
        "33140000-073032-42574629",
        "33140000-073033-42574629",
        "33140000-073092-42574629",
        "33140000-073093-42574629",
        "33140000-073094-42574629",
        "33140000-073095-42574629",
        "33140000-511202-42574629",
        "33140000-614919-42574629",
        "33140000-287334-42574629",
        "33140000-548016-42574629",
        "33140000-715091-42574629",
        "33141200-904321-42574629",
        "33141600-862600-42574629",
        "33140000-904342-42574629",
        "33140000-904343-42574629",
        "33140000-904345-42574629",
        "33140000-904346-42574629",
        "33140000-112614-42574629",
        "33141120-000001-42574629",
        "33141000-000001-42574629",
        "33141000-000002-42574629",
    ): {
        "classification.id": "33141000-0",
        "classification.description": "Медичні матеріали нехімічні та гематологічні одноразового застосування",
    },
    (
        "33140000-949200-42574629",
        "33140000-560716-42574629",
        "33140000-247331-42574629",
        "33140000-643204-42574629",
        "33140000-637097-42574629",
        "33140000-367122-42574629",
        "33140000-493597-42574629",
        "33140000-290057-425746299",
        "33140000-369855-42574629",
        "33140000-212121-42574629",
        "33140000-733122-42574629",
        "33140000-142148-42574629",
        "33140000-585858-42574629",
        "33140000-133022-42574629",
        "33140000-073090-42574629",
        "33140000-073091-42574629",
    ): {
        "classification.id": "33141110-4",
        "classification.description": "Перев’язувальні матеріали",
    },
    (
        "33140000-177201-42574629",
        "33140000-910858-42574629",
        "33140000-123485-42574629",
        "33140000-370795-42574629",
        "33140000-826558-42574629",
        "33140000-919063-42574629",
        "33140000-787202-42574629",
        "33140000-806708-42574629",
        "33140000-180018-42574629",
        "33140000-851236-42574629",
        "33140000-135634-42574629",
        "33140000-135635-42574629",
        "33140000-931756-42574629",
        "33140000-412447-42574629",
        "33140000-851237-42574629",
     ): {
        "classification.id": "33141600-6",
        "classification.description": "Контейнери та пакети для забору матеріалу для аналізів, дренажі та комплекти",
    },
    (
        "33140000-432610-42574629",
        "33140000-130782-425746299",
        "33140000-803628-425746299",
        "33140000-574922-425746299",
        "33140000-444870-425746299",
        "33140000-331083-42574629",
        "33140000-218680-42574629",
        "33140000-717920-42574629",
        "33140000-373737-42574629",
        "33140000-904270-42574629",
        "33141300-904319-42574629",
        "33141300-904320-42574629",
     ): {
        "classification.id": "33141300-3",
        "classification.description": "Приладдя для венепункції та забору крові",
    },
}


async def migrate_categories():
    logger.info("Start MZU categories' fields migration")
    counter = 0
    bulk = []
    category_collection = get_category_collection()

    for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
        async for category in category_collection.find(
            {"_id": {"$in": category_ids}},
        ):
            update_data["dateModified"] = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": category["_id"]},
                    update={"$set": update_data},
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

    with open('cs_20538_mzu_profiles.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["id", "relatedCategory", "title"], extrasaction="ignore")
        writer.writeheader()
        for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
            async for obj in obj_collection.find(
                {"relatedCategory": {"$in": category_ids}},
            ):
                update_data["dateModified"] = get_now().isoformat()
                bulk.append(
                    UpdateOne(
                        filter={"_id": obj["_id"]},
                        update={"$set": update_data},
                    )
                )
                profile_data = {
                    "id": obj["_id"],
                    "relatedCategory": obj["relatedCategory"],
                    "title": obj["title"],
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
            {"relatedCategory": {"$in": category_ids}},
        ):
            update_data["dateModified"] = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": update_data},
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
