import asyncio
import logging
import sentry_sdk
from uuid import uuid4
from copy import deepcopy

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_profiles_collection,
    get_category_collection,
    get_products_collection,
)
from catalog.logging import setup_logging
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.settings import SENTRY_DSN
from catalog.utils import get_now


logger = logging.getLogger(__name__)


CATEGORY_ID = "99999999-919912-02426097"


NEW_CRITERIA_DATA = [
    {
        "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
        "description": "Товар включений до додаткового переліку, що затверджений "
                       "Кабінетом Міністрів України, і має ступінь локалізації виробництва, "
                       "який перевищує або дорівнює ступеню локалізації виробництва, встановленому "
                       "на відповідний рік. Ці вимоги не застосовуються до закупівель, які підпадають під дію "
                       "положень Закону України \"Про приєднання України до Угоди про державні закупівлі\", а "
                       "також положень про державні закупівлі інших міжнародних договорів України, згода на "
                       "обов’язковість яких надана Верховною Радою України.",
        "classification": {
            "scheme": "ESPD211",
            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"
        },
        "legislation": [
            {
                "version": "2021-12-16",
                "type": "NATIONAL_LEGISLATION",
                "article": "1.4.1",
                "identifier": {
                    "uri": "https://zakon.rada.gov.ua/laws/show/1977-20",
                    "id": "1977-IX",
                    "legalName": "Про внесення змін до Закону України "
                                 "\"Про публічні закупівлі\" щодо створення передумов "
                                 "для сталого розвитку та модернізації вітчизняної промисловості"
                }
            },
            {
                "version": "2023-04-11",
                "type": "NATIONAL_LEGISLATION",
                "article": "1.4",
                "identifier": {
                    "uri": "https://zakon.rada.gov.ua/laws/show/861-2022-%D0%BF",
                    "id": "861-2022-п",
                    "legalName": "Про затвердження порядків підтвердження "
                                 "ступеня локалізації виробництва товарів та "
                                 "проведення моніторингу дотримання вимог щодо "
                                 "ступеня локалізації виробництва предметів закупівлі, "
                                 "внесених до переліку товарів, що є предметом закупівлі, "
                                 "з підтвердженим ступенем локалізації виробництва"
                }
            }
        ],
        "source": "tenderer",
        "requirementGroups": [
            {
                "description": "За наявності складових вітчизняного виробництва "
                               "у собівартості товару, підтверджується, що",
                "requirements": [
                    {
                        "title": "Ступінь локалізації виробництва товару, що є предметом закупівлі, "
                                 "перевищує або дорівнює ступеню локалізації виробництва, "
                                 "встановленому на відповідний рік",
                        "dataType": "number",
                        "minValue": 20,
                        "unit": {
                            "name": "Відсоток",
                            "code": "P1"
                        }
                    }
                ]
            },
            {
                "description": "За відсутності складових вітчизняного виробництва "
                               "у собівартості товару, підтверджується, що",
                "requirements": [
                    {
                        "title": "Товар походить з однієї з країн, що підписала "
                                 "Угоду про державні закупівлі Світової Організації "
                                 "торгівлі (GPA) або іншої країни з якою Україна "
                                 "має міжнародні договори про державні закупівлі",
                        "dataType": "string",
                        "expectedValues": [
                            "AM",
                            "AU",
                            "CA",
                            "AT",
                            "BE",
                            "BG",
                            "HR",
                            "CY",
                            "EE",
                            "CZ",
                            "DK",
                            "FI",
                            "FR",
                            "GR",
                            "ES",
                            "NL",
                            "IE",
                            "LT",
                            "LU",
                            "LV",
                            "MT",
                            "DE",
                            "PL",
                            "PT",
                            "RO",
                            "SK",
                            "SI",
                            "SE",
                            "HU",
                            "IT",
                            "IL",
                            "MD",
                            "ME",
                            "HK",
                            "IS",
                            "JP",
                            "KR",
                            "LI",
                            "AW",
                            "NZ",
                            "MK",
                            "NO",
                            "SG",
                            "CH",
                            "TW",
                            "GB",
                            "US"
                        ]
                    }
                ]
            }
        ]
    }
]

LOCALIZATION_REQ_TITLE = NEW_CRITERIA_DATA[0]["requirementGroups"][0]["requirements"][0]["title"]


def generate_id():
    return uuid4().hex


def get_new_criteria_data():
    criteria_data = deepcopy(NEW_CRITERIA_DATA)

    for criterion in criteria_data:
        criterion["id"] = generate_id()
        for rg in criterion["requirementGroups"]:
            rg["id"] = generate_id()

            for req in rg["requirements"]:
                req["id"] = generate_id()
                for ev in req.get("eligibleEvidences", ""):
                    ev["id"] = generate_id()

    return criteria_data


async def migrate_categories(session):
    bulk = []
    counter = 0
    get_new_criteria_data()
    collection = get_category_collection()
    async for obj in collection.find(
        {"_id": CATEGORY_ID},
        projection={"_id": 1, "criteria": 1}
    ):
        counter += 1
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$set": {"criteria": get_new_criteria_data(), "dateModified": now}}
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="categories")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="categories")

    logger.info(f"Finished. Processed {counter} records of migrated categories")


async def migrate_profiles(session):
    bulk = []
    counter = 0
    collection = get_profiles_collection()
    async for obj in collection.find(
        {"relatedCategory": CATEGORY_ID, "status": {"$ne": "hidden"}},
        projection={"_id": 1, "criteria": 1}
    ):
        counter += 1
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$set": {"criteria": get_new_criteria_data(), "dateModified": now}}
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="profiles")

    logger.info(f"Finished. Processed {counter} records of migrated profiles")


async def migrate_products(session):
    bulk = []
    counter = 0
    collection = get_products_collection()
    async for obj in collection.find(
        {"relatedCategory": CATEGORY_ID, "status": {"$ne": "hidden"}},
        projection={"_id": 1, "requirementResponses": 1}
    ):
        counter += 1
        obj["requirementResponses"][0]["requirement"] = LOCALIZATION_REQ_TITLE
        now = get_now().isoformat()
        bulk.append(
            UpdateOne(
                filter={"_id": obj["_id"]},
                update={"$set": {"requirementResponses": obj["requirementResponses"], "dateModified": now}}
            )
        )

        if bulk and len(bulk) % 500 == 0:
            await bulk_update(collection, bulk, session, counter, migrated_obj="products")
            bulk = []

    if bulk:
        await bulk_update(collection, bulk, session, counter, migrated_obj="products")

    logger.info(f"Finished. Processed {counter} records of migrated products")


async def migrate():
    logger.info("Start migration")
    async with transaction_context_manager() as session:
        await migrate_categories(session)
        await migrate_profiles(session)
        await migrate_products(session)
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
