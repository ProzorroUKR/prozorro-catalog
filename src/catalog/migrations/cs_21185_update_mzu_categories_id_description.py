import asyncio
import csv
import logging

import sentry_sdk
from pymongo import UpdateOne

from catalog.db import (
    get_category_collection,
    get_products_collection,
    get_profiles_collection,
    init_mongo,
    transaction_context_manager,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now

logger = logging.getLogger(__name__)

MZU_CATEGORIES_FIELDS_MAPPING = {
    (
        "33140000-222021-42574629",
    ): {
        "classification.id": "33141110-4",
        "classification.description": "Перев'язувальні матеріали",
    },
    (
        "33140000-000001-42574629",
    ): {
        "classification.id": "33141000-0",
        "classification.description": "Медичні матеріали нехімічні та гематологічні одноразового застосування",
    },
    (
        "33190000-691520-425746299",
        "33190000-818867-425746299",
        "33190000-834166-425746299",
        "33190000-142142-42574629",
        "33190000-000002-42574629",
        "33190000-000003-42574629",
        "33190000-000004-42574629",
        "33190000-000005-42574629",
        "33190000-000006-42574629",
        "33190000-000007-42574629",
    ): {
        "classification.id": "33120000-7",
        "classification.description": "Системи реєстрації медичної інформації та дослідне обладнання",
    },
    (
        "33190000-146642-42574629",
        "33199000-909090-42574629",
    ): {
        "classification.id": "33199000-1",
        "classification.description": "Одяг для медичного персоналу",
    },
    (
        "33190000-798649-42574629",
        "33190000-898226-425746299",
        "33190000-457412-42574629",
        "33190000-667090-42574629",
        "33190000-528856-425746299",
        "33190000-212121-42574629",
        "33190000-121212-42574629",
    ): {
        "classification.id": "33191000-5",
        "classification.description": "Обладнання стерилізаційне, дезінфекційне та санітарно-гігієнічне",
    },
    (
        "33190000-505291-42574629",
        "33190000-739753-42574629",
    ): {
        "classification.id": "33195000-3",
        "classification.description": "Системи моніторингу стану пацієнта",
    },
    (
        "33190000-381229-42574629",
        "33190000-216688-42574629",
    ): {
        "classification.id": "33196000-0",
        "classification.description": "Аптечки першої медичної допомоги",
    },
    (
        "33190000-219405-42574629",
        "33190000-830586-42574629",
        "33190000-609428-42574629",
        "33190000-938418-42574629",
        "33190000-482822-42574629",
        "33190000-583591-42574629",
        "33190000-376914-42574629",
        "33190000-427053-42574629",
        "33190000-345202-42574629",
        "33190000-515306-42574629",
        "33190000-692186-42574629",
        "33190000-822210-42574629",
        "33690000-176698-42574629",
        "33192000-000002-42574629",
        "33192000-000003-42574629",
        "33192000-000004-42574629",
        "33192000-000005-42574629",
        "33192000-000007-42574629",
        "4bbcc1136f1f4cb180cc9430428edea5",
    ): {
        "classification.id": "33192000-2",
        "classification.description": "Меблі медичного призначення",
    },
    (
        "33190000-717171-42574629",
        "33194000-000001-42574629",
    ): {
        "classification.id": "33141300-3",
        "classification.description": "Приладдя для венепункції та забору крові",
    },
    (
        "33192500-000001-42574629",
    ): {
        "classification.id": "33141600-6",
        "classification.description": "Контейнери та пакети для забору матеріалу для аналізів, дренажі та комплекти",
    },
}


async def migrate_categories():
    logger.info("Start MZU categories' fields migration (BS-8376)")
    counter = 0
    bulk = []
    category_collection = get_category_collection()

    for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
        async for category in category_collection.find(
            {"_id": {"$in": category_ids}},
        ):
            update_fields = {
                "classification.id": update_data["classification.id"],
                "classification.description": update_data["classification.description"],
                "dateModified": get_now().isoformat(),
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
    logger.info("Start MZU profiles migration (BS-8376)")
    counter = 0
    bulk = []

    with open("/tmp/cs_21185_mzu_profiles.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["id", "relatedCategory", "title", "classification.id", "classification.description"],
            extrasaction="ignore",
        )
        writer.writeheader()

        for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
            async for obj in obj_collection.find(
                {"relatedCategory": {"$in": category_ids}},
            ):
                update_fields = {
                    "classification.id": update_data["classification.id"],
                    "classification.description": update_data["classification.description"],
                    "dateModified": get_now().isoformat(),
                }
                bulk.append(
                    UpdateOne(
                        filter={"_id": obj["_id"]},
                        update={"$set": update_fields},
                    )
                )
                writer.writerow(
                    {
                        "id": obj["_id"],
                        "relatedCategory": obj["relatedCategory"],
                        "title": obj["title"],
                        "classification.id": update_data["classification.id"],
                        "classification.description": update_data["classification.description"],
                    }
                )
                counter += 1

                if bulk and len(bulk) % 500 == 0:
                    async with transaction_context_manager() as session:
                        await bulk_update(obj_collection, bulk, session, counter, migrated_obj="profiles")
                    bulk = []

        if bulk:
            async with transaction_context_manager() as session:
                await bulk_update(obj_collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} updated profiles.")


async def migrate_products():
    obj_collection = get_products_collection()
    logger.info("Start MZU products migration (cs-21185)")
    counter = 0
    bulk = []

    for category_ids, update_data in MZU_CATEGORIES_FIELDS_MAPPING.items():
        async for obj in obj_collection.find(
            {"relatedCategory": {"$in": category_ids}},
        ):
            update_fields = {
                "classification.id": update_data["classification.id"],
                "classification.description": update_data["classification.description"],
                "dateModified": get_now().isoformat(),
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

    logger.info(f"Finished. Processed {counter} updated products.")


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


if __name__ == "__main__":
    main()