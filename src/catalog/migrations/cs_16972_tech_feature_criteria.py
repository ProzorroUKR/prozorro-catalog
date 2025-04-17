import asyncio
import logging
from copy import deepcopy

import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
    get_category_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN, TECHNICAL_FEATURES_CRITERIA
from catalog.utils import get_now

logger = logging.getLogger(__name__)


EXCLUDE_CATEGORY_ID = "99999999-919912-02426097"


CRITERIA_ADDITIONAL_DATA = {
    "title": "Технічні, якісні та кількісні характеристики предмета закупівлі",
    "description": "Технічна специфікація повинна містити опис усіх необхідних характеристик товарів, робіт "
                   "або послуг, що закуповуються, у тому числі їх технічні, функціональні та якісні характеристики. "
                   "Характеристики товарів, робіт або послуг можуть містити опис конкретного технологічного процесу "
                   "або технології виробництва чи порядку постачання товару (товарів), виконання необхідних робіт, "
                   "надання послуги (послуг)",
    "classification": {
        "scheme": "ESPD211",
        "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES"
    },
    "legislation": [
        {
            "version": "2024-04-19",
            "type": "NATIONAL_LEGISLATION",
            "identifier": {
                "uri": "https://zakon.rada.gov.ua/laws/show/922-19#n1398",
                "id": "922-VIII",
                "legalName": "Закон України \"Про публічні закупівлі\""
            },
            "article": "22.2.3"
        },
        {
            "version": "2024-04-19",
            "type": "NATIONAL_LEGISLATION",
            "identifier": {
                "uri": "https://zakon.rada.gov.ua/laws/show/922-19#n1426",
                "id": "922-VIII",
                "legalName": "Закон України \"Про публічні закупівлі\""
            },
            "article": "23"
        },
        {
            "version": "2023-10-31",
            "type": "NATIONAL_LEGISLATION",
            "identifier": {
                "uri": "https://zakon.rada.gov.ua/laws/show/1135-2023-%D0%BF#n24",
                "id": "1135-2023-п",
                "legalName": "Про внесення змін до постанов Кабінету Міністрів України "
                             "від 14 вересня 2020 р. № 822 і від 12 жовтня 2022 р. № 1178"
            },
            "article": "2.1"
        }
    ],
    "source": "tenderer",
}

NEW_CRITERION_RG_DATA = {
    "description": "Підтверджується, що"
}


def update_criteria(criteria):
    updated = False
    for criterion in criteria:
        previous_criterion = deepcopy(criterion)
        if criterion["classification"]["id"] == TECHNICAL_FEATURES_CRITERIA:
            criterion.update(CRITERIA_ADDITIONAL_DATA)
            for rg in criterion.get("requirementGroups", ""):
                rg.update(NEW_CRITERION_RG_DATA)
            if previous_criterion != criterion:
                updated = True
    return criteria if updated else None


async def migrate_categories():
    bulk = []
    counter = 0
    collection = get_category_collection()
    async for obj in collection.find(
        {"_id": {"$ne": EXCLUDE_CATEGORY_ID}, "criteria": {"$exists": True}},
        projection={"_id": 1, "criteria": 1}
    ):
        if updated_criteria := update_criteria(obj["criteria"]):
            counter += 1
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"criteria": updated_criteria, "dateModified": now}}
                )
            )

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} records of migrated categories")


async def migrate_profiles():
    bulk = []
    counter = 0
    collection = get_profiles_collection()
    async for obj in collection.find(
        {"relatedCategory": {"$ne": EXCLUDE_CATEGORY_ID}, "criteria": {"$exists": True}},
        projection={"_id": 1, "criteria": 1}
    ):
        if updated_criteria := update_criteria(obj["criteria"]):
            counter += 1
            now = get_now().isoformat()
            bulk.append(
                UpdateOne(
                    filter={"_id": obj["_id"]},
                    update={"$set": {"criteria": updated_criteria, "dateModified": now}}
                )
            )

        if bulk and len(bulk) % 500 == 0:
            async with transaction_context_manager() as session:
                await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")
            bulk = []

    if bulk:
        async with transaction_context_manager() as session:
            await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} records of migrated profiles")


async def migrate():
    logger.info("Start migration")
    await migrate_categories()
    await migrate_profiles()
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
