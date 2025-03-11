import asyncio
from uuid import uuid4
from copy import deepcopy

import logging
import sentry_sdk

from pymongo import UpdateOne

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
    get_profiles_collection,
    get_products_collection,
)
from catalog.migrations.cs_16303_requirement_iso_migration import bulk_update
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


PROFILE_MAPPING = {
    "Генератори": {
        "class_id": "31120000-3",
        "profiles": [],
    },
    "Генераторні установки з двигуном із іскровим запалюванням": {
        "class_id": "31120000-3",
        "profiles": [
            "999913-99999999-919998-02426097",
        ]
    },
    "Турбогенераторні установки": {
        "class_id": "31120000-3",
        "profiles": [
            "999914-99999999-919998-02426097",
        ]
    },
    "Дизель-генераторні установки": {
        "class_id": "31120000-3",
        "profiles": [
            "999912-99999999-919998-02426097",
        ]
    },
    "Трансформатори": {
        "class_id": "31170000-8",
        "profiles": [
            "999915-99999999-919998-02426097",
            "999916-99999999-919998-02426097",
            "999917-99999999-919998-02426097",
            "999918-99999999-919998-02426097",
            "999919-99999999-919998-02426097",
        ]
    },
    "Електронне обладнання (конденсатори)": {
        "class_id": "31710000-6",
        "profiles": [
            "999920-99999999-919998-02426097",
            "999921-99999999-919998-02426097",
            "999922-99999999-919998-02426097",
        ]
    },
    "Автомобілі швидкої допомоги": {
        "class_id": "34114121-3",
        "profiles": ["999923-99999999-919998-02426097",]
    },
    "Транспортні засоби для перевезення пацієнтів": {
        "class_id": "34114122-0",
        "profiles": ["999924-99999999-919998-02426097",]
    },
    "Шкільні автобуси": {
        "class_id": "34120000-4",
        "profiles": ["999925-99999999-919998-02426097",]
    },
    "Міські та туристичні автобуси": {
        "class_id": "34121000-1",
        "profiles": [
            "999926-99999999-919998-02426097",
            "999927-99999999-919998-02426097",
            "999928-99999999-919998-02426097",
            "999929-99999999-919998-02426097",
            "999930-99999999-919998-02426097",
        ]
    },
    "Мототранспортні вантажні засоби (автоцистерни, самоскиди та фургони)": {
        "class_id": "34130000-7",
        "profiles": [
            "999931-99999999-919998-02426097",
            "999932-99999999-919998-02426097",
            "999933-99999999-919998-02426097",
            "999934-99999999-919998-02426097",
            "999935-99999999-919998-02426097"
        ]
    },
    "Великовантажні мототранспортні засоби (від автокранів, сміттєвозів до єлектробусів)": {
        "class_id": "34140000-0",
        "profiles": [
            "999936-99999999-919998-02426097",
            "999937-99999999-919998-02426097",
            "999938-99999999-919998-02426097",
            "999939-99999999-919998-02426097",
            "999940-99999999-919998-02426097",
            "999941-99999999-919998-02426097",
            "999942-99999999-919998-02426097",
            "999943-99999999-919998-02426097",
            "999944-99999999-919998-02426097",
            "999945-99999999-919998-02426097",
            "999946-99999999-919998-02426097",
            "999947-99999999-919998-02426097"
            "999948-99999999-919998-02426097",
            "999949-99999999-919998-02426097",
            "999950-99999999-919998-02426097",
            "999951-99999999-919998-`02426097",
            "999952-99999999-919998-02426097",
            "999953-99999999-919998-02426097",
            "999954-99999999-919998-02426097",
        ]
    },
    "Кузови транспортних засобів": {
        "class_id": "34210000-2",
        "profiles": [
            "999956-99999999-919998-02426097",
        ]
    },
    "Причепи, напівпричепи та пересувні контейнери": {
        "class_id": "34220000-5",
        "profiles": [
            "999957-99999999-919998-02426097",
            "999958-99999999-919998-02426097",
            "999959-99999999-919998-02426097",
            "999960-99999999-919998-02426097",
            "999961-99999999-919998-02426097",
        ]
    },
    "Залізничні локомотиви та тендери": {
        "class_id": "34610000-6",
        "profiles": [
            "999963-99999999-919998-02426097",
            "999964-99999999-919998-02426097",
            "999965-99999999-919998-02426097",
        ]
    },
    "Рейковий рухомий склад (засоби для ремонту, вантажні та пасажирські вагони, тролейбуси)": {
        "class_id": "34620000-9",
        "profiles": [
            "999966-99999999-919998-02426097",
            "999967-99999999-919998-02426097",
            "999968-99999999-919998-02426097",
            "999969-99999999-919998-02426097",
            "999970-99999999-919998-02426097",
            "999971-99999999-919998-02426097",
            "999972-99999999-919998-02426097",
            "999973-99999999-919998-02426097",
            "999974-99999999-919998-02426097",
        ]
    },
    "Самохідні частини": {
        "class_id": "34640000-5",
        "profiles": ["999975-99999999-919998-02426097",]
    },
    "Безпілотні літальні апарати мультироторного типу (FPV)": {
        "class_id": "34710000-7",
        "profiles": [],
    },
    "Вертольоти, літаки, космічні та інші літальні апарати з двигуном": {
        "class_id": "34710000-7",
        "profiles": [
            "999976-99999999-919998-02426097",
            "999977-99999999-919998-02426097",
            "999978-99999999-919998-02426097",
        ]
    },
    "Частини повітряних літальних апаратів": {
        "class_id": "34731000-0",
        "profiles": [
            "999979-99999999-919998-02426097",
            "999980-99999999-919998-02426097",
            "999981-99999999-919998-02426097",
            "999982-99999999-919998-02426097"
        ]
    },
    "Військові літаки (навчально-тренувальні літаки та пошуково-рятувальні вертольоти)": {
        "class_id": "35610000-3",
        "profiles": [
            "999983-99999999-919998-02426097",
            "999984-99999999-919998-02426097"
        ]
    },
    "Турбіни та мотори (парові, гідравлічні та спеціального призначення)": {
        "class_id": "42110000-3",
        "profiles": [
            "999985-99999999-919998-02426097",
            "999986-99999999-919998-02426097",
            "999987-99999999-919998-02426097",
            "999988-99999999-919998-02426097",
        ]
    },
    "Компресори": {
        "class_id": "42120000-6",
        "profiles": [
            "999196-99999999-919998-02426097",
            "999195-99999999-919998-02426097",
            "999194-99999999-919998-02426097",
            "999193-99999999-919998-02426097",
            "999192-99999999-919998-02426097",
            "999191-99999999-919998-02426097",
        ]
    },
    "Насоси": {
        "class_id": "42120000-6",
        "profiles": [
            "999989-99999999-919998-02426097",
            "999990-99999999-919998-02426097",
            "999991-99999999-919998-02426097",
            "999199-99999999-919998-02426097",
            "999198-99999999-919998-02426097",
            "999197-99999999-919998-02426097",
        ]
    },
    "Машини спеціального призначення різні": {
        "class_id": "42990000-2",
        "profiles": ["999190-99999999-919998-02426097",]
    },
    "Врубові та тунелепрохідні, бурильні чи прохідницькі машини для добування вугілля чи гірських порід": {
        "class_id": "43120000-0",
        "profiles": [
            "999188-99999999-919998-02426097",
            "999187-99999999-919998-02426097",
            "999186-99999999-919998-02426097",
        ]
    },
    "Машини для земляних робіт": {
        "class_id": "43210000-8",
        "profiles": ["999184-99999999-919998-02426097"]
    },
    "Фронтальні ковшові навантажувачі": {
        "class_id": "43250000-0",
        "profiles": ["999183-99999999-919998-02426097"]
    },
    "Механічні лопати, екскаватори та ковшові навантажувачі, гірнича техніка": {
        "class_id": "43260000-3",
        "profiles": [
            "999182-99999999-919998-02426097",
            "999181-99999999-919998-02426097",
            "999180-99999999-919998-02426097",
            "999179-99999999-919998-02426097",
            "999178-99999999-919998-02426097"
        ]
    },
    "Машини для обробки мінералів": {
        "class_id": "43410000-0",
        "profiles": ["999177-99999999-919998-02426097"]
    },
}

PROFILES_TO_HIDDEN = [
    "999955-99999999-919998-02426097",
    "999962-99999999-919998-02426097",
    "999189-99999999-919998-02426097",
    "999185-99999999-919998-02426097",
]

PROFILES_IDS = [
    "999937-99999999-919998-02426097",
    "999923-99999999-919998-02426097",
    "999932-99999999-919998-02426097",
    "999933-99999999-919998-02426097",
    "999974-99999999-919998-02426097",
    "999938-99999999-919998-02426097",
    "999939-99999999-919998-02426097",
    "999967-99999999-919998-02426097",
    "999953-99999999-919998-02426097",
    "999936-99999999-919998-02426097",
    "999978-99999999-919998-02426097",
    "999977-99999999-919998-02426097",
    "999976-99999999-919998-02426097",
    "999918-99999999-919998-02426097",
    "999197-99999999-919998-02426097",
    "999199-99999999-919998-02426097",
    "999988-99999999-919998-02426097",
    "999188-99999999-919998-02426097",
    "999195-99999999-919998-02426097",
    "999913-99999999-919998-02426097",
    "999987-99999999-919998-02426097",
    "999189-99999999-919998-02426097",
    "999927-99999999-919998-02426097",
    "999979-99999999-919998-02426097",
    "999928-99999999-919998-02426097",
    "999912-99999999-919998-02426097",
    "999920-99999999-919998-02426097",
    "999954-99999999-919998-02426097",
    "999973-99999999-919998-02426097",
    "999963-99999999-919998-02426097",
    "999971-99999999-919998-02426097",
    "999962-99999999-919998-02426097",
    "999969-99999999-919998-02426097",
    "999179-99999999-919998-02426097",
    "999196-99999999-919998-02426097",
    "999922-99999999-919998-02426097",
    "999921-99999999-919998-02426097",
    "999956-99999999-919998-02426097",
    "999955-99999999-919998-02426097",
    "999964-99999999-919998-02426097",
    "999965-99999999-919998-02426097",
    "999185-99999999-919998-02426097",
    "999184-99999999-919998-02426097",
    "999177-99999999-919998-02426097",
    "999190-99999999-919998-02426097",
    "999178-99999999-919998-02426097",
    "999180-99999999-919998-02426097",
    "999181-99999999-919998-02426097",
    "999182-99999999-919998-02426097",
    "999926-99999999-919998-02426097",
    "999931-99999999-919998-02426097",
    "999925-99999999-919998-02426097",
    "999940-99999999-919998-02426097",
    "999983-99999999-919998-02426097",
    "999959-99999999-919998-02426097",
    "999990-99999999-919998-02426097",
    "999991-99999999-919998-02426097",
    "999989-99999999-919998-02426097",
    "999929-99999999-919998-02426097",
    "999986-99999999-919998-02426097",
    "999941-99999999-919998-02426097",
    "999198-99999999-919998-02426097",
    "999948-99999999-919998-02426097",
    "999947-99999999-919998-02426097",
    "999193-99999999-919998-02426097",
    "999945-99999999-919998-02426097",
    "999943-99999999-919998-02426097",
    "999944-99999999-919998-02426097",
    "999942-99999999-919998-02426097",
    "999949-99999999-919998-02426097",
    "999191-99999999-919998-02426097",
    "999984-99999999-919998-02426097",
    "999960-99999999-919998-02426097",
    "999961-99999999-919998-02426097",
    "999958-99999999-919998-02426097",
    "999957-99999999-919998-02426097",
    "999187-99999999-919998-02426097",
    "999186-99999999-919998-02426097",
    "999982-99999999-919998-02426097",
    "999966-99999999-919998-02426097",
    "999194-99999999-919998-02426097",
    "999934-99999999-919998-02426097",
    "999975-99999999-919998-02426097",
    "999951-99999999-919998-02426097",
    "999950-99999999-919998-02426097",
    "999952-99999999-919998-02426097",
    "999970-99999999-919998-02426097",
    "999946-99999999-919998-02426097",
    "999924-99999999-919998-02426097",
    "999968-99999999-919998-02426097",
    "999915-99999999-919998-02426097",
    "999919-99999999-919998-02426097",
    "999916-99999999-919998-02426097",
    "999917-99999999-919998-02426097",
    "999972-99999999-919998-02426097",
    "999985-99999999-919998-02426097",
    "999981-99999999-919998-02426097",
    "999914-99999999-919998-02426097",
    "999192-99999999-919998-02426097",
    "999980-99999999-919998-02426097",
    "999930-99999999-919998-02426097",
    "999183-99999999-919998-02426097",
    "999935-99999999-919998-02426097",
]

SPECIAL_CATEGORIES_CLASSIFICATIONS = ("34114121-3", "34710000-7", "31120000-3", "34120000-4", "42120000-6")

LOCALIZATION_CRITERION_DATA = {
    "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
    "description": "Товар включений до додаткового переліку, що затверджений "
                   "Кабінетом Міністрів України, і має ступінь локалізації виробництва, "
                   "який перевищує або дорівнює ступеню локалізації виробництва, встановленому "
                   "на відповідний рік. Ці вимоги не застосовуються до закупівель, які підпадають під дію "
                   "положень Закону України \"Про приєднання України до Угоди про державні закупівлі\", а "
                   "також положень про державні закупівлі інших міжнародних договорів України, згода на "
                   "обов’язковість яких надана Верховною Радою України",
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
                    "minValue": 25.0,
                    "unit": {
                        "name": "відсоток",
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
                    "expectedMinItems": 1,
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


PRODUCTS_CLASSIFICATION_MAPPING = {
    "34200000-9": {
        "title": "Кузови транспортних засобів",
        "classification": {
            "id": "34210000-2",
            "description": "Кузови транспортних засобів",
            "schema": "ДК021"
        }
    },
    "34600000-3": {
        "title": "Залізничні локомотиви та тендери",
        "classification": {
            "id": "34610000-6",
            "description": "Залізничні локомотиви та тендери",
            "schema": "ДК021"
        }
    },
    "43000000-3": {
        "title": "Врубові та тунелепрохідні, бурильні чи прохідницькі машини для добування вугілля чи гірських порід",
        "classification": {
            "id": "43120000-0",
            "description": "Врубові та тунелепрохідні, бурильні чи прохідницькі машини для добування вугілля чи гірських порід",
            "schema": "ДК021"
        }
    },
    "43200000-5": {
        "title": "Машини для земляних робіт",
        "classification": {
            "id": "43210000-8",
            "description": "Машини для земляних робіт",
            "schema": "ДК021"
        }
    },
}


def get_localization_criteria() -> dict:
    localization_criteria = deepcopy(LOCALIZATION_CRITERION_DATA)
    for c in [localization_criteria]:
        c["id"] = uuid4().hex
        for rg in c.get("requirementGroups", ""):
            rg["id"] = uuid4().hex
            for req in rg.get("requirements", ""):
                req["id"] = uuid4().hex

    return localization_criteria


def set_new_localization_criteria(category_criteria: list) -> list:
    localization_criteria = get_localization_criteria()

    is_lc_exist = False
    for i, value in enumerate(category_criteria):
        if value["classification"]["id"] == "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL":
            is_lc_exist = True
            category_criteria[i] = localization_criteria

    if not is_lc_exist:
        category_criteria.append(localization_criteria)

    return category_criteria


async def migrate_categories():
    logger.info("Start categories migration of set localization criteria to specialized categories")
    category_collection = get_category_collection()

    counter = 0
    async with transaction_context_manager() as session:
        async for category in category_collection.find(
                {"classification.id": {"$in": SPECIAL_CATEGORIES_CLASSIFICATIONS}},
                {"criteria": 1},

        ):
            updated_category_criteria = set_new_localization_criteria(category.get("criteria", []))
            try:
                await category_collection.update_one(
                    {"_id": category["_id"]},
                    {"$set": {"criteria": updated_category_criteria, "dateModified": get_now().isoformat()}},
                    session=session,
                )
                counter += 1
            except Exception as e:
                logger.error(f"Category {category['_id']} not updated, cause error: {e}")
                raise e

    logger.info(f"Finished. Processed {counter} updated categories")
    logger.info("Successfully migrated")


async def migrate_profiles():
    logger.info("Start localized profiles migration of set relatedCategory matched by classification.id")
    counter = 0

    category_collection = get_category_collection()
    profiles_collection = get_profiles_collection()

    async with transaction_context_manager() as session:
        # Hide profiles
        async for hidden_profile in profiles_collection.find(
            {"_id": {"$in": PROFILES_TO_HIDDEN}},
        ):
            try:
                await profiles_collection.update_one(
                    {"_id": hidden_profile["_id"]},
                    {"$set": {"status": "hidden", "dateModified": get_now().isoformat()}},
                    session=session,
                )
                counter += 1
            except Exception as e:
                logger.error(f"Profile {hidden_profile['_id']} didn't become hidden, cause error: {e}")
                raise e

        # Relate categories with profiles
        for title, class_data in PROFILE_MAPPING.items():
            async for profile in profiles_collection.find(
                {"_id": {"$in": class_data["profiles"]}},
                {"classification": 1, "criteria": 1},
            ):
                classification_id = profile["classification"]["id"]
                category = await category_collection.find_one_and_update(
                    filter={"classification.id": class_data["class_id"], "title": title},
                    update={"$set": {"status": "active"}},
                    projection={"_id": 1, "agreementID": 1},
                    sort={"dateModified": -1}
                )

                if not category:
                    continue

                if category:
                    updated_data = {"relatedCategory": category["_id"], "dateModified": get_now().isoformat()}
                    if classification_id in SPECIAL_CATEGORIES_CLASSIFICATIONS:
                        if agreement_id := category.get("agreementID"):
                            updated_data["agreementID"] = agreement_id

                for c in profile.get("criteria", ""):
                    if c["classification"]["id"] == "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL":
                        c["requirementGroups"][0]["requirements"][0]["minValue"] = 25.0
                        updated_data["criteria"] = profile["criteria"]
                        break
                try:
                    await profiles_collection.update_one(
                        {"_id": profile["_id"]},
                        {"$set": updated_data},
                        session=session,
                    )
                    counter += 1
                except Exception as e:
                    logger.error(f"Profile {profile['_id']} not updated, cause error: {e}")
                    raise e

    logger.info(f"Finished. Processed {counter} updated profiles")
    logger.info("Successfully migrated")


async def migrate_product_classification():
    logger.info("Start localized products migration for changing classification id")
    counter = 0
    bulk = []
    category_collection = get_category_collection()
    products_collection = get_products_collection()
    # Migrate products classification for hidden profiles
    for prev_class_id, new_product_data in PRODUCTS_CLASSIFICATION_MAPPING.items():
        async for product in products_collection.find(
                {"classification.id": prev_class_id},
                {"classification": 1},
        ):
            updated_data = {
                "classification": new_product_data["classification"],
                "dateModified": get_now().isoformat(),
            }
            category = await category_collection.find_one(
                filter={"classification.id": new_product_data["classification"]["id"], "title": new_product_data["title"]},
                projection={"_id": 1},
                sort={"dateModified": -1}
            )
            if category:
                updated_data["relatedCategory"] = category["_id"]
            bulk.append(
                UpdateOne(
                    filter={"_id": product["_id"]},
                    update={"$set": updated_data}
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

    logger.info(f"Finished. Processed {counter} updated products' classification.")


async def migrate_products_related_category():
    logger.info("Start localized products migration of set relatedCategory matched by classification.id")
    counter = 0
    bulk = []
    profiles_collection = get_profiles_collection()
    products_collection = get_products_collection()
    async for product in products_collection.find(
        {"relatedProfiles": {"$in": PROFILES_IDS}},
        {"relatedProfiles": 1},
    ):
        profile = await profiles_collection.find_one(
            {"_id": product["relatedProfiles"][0]},
            {"relatedCategory": 1},
        )
        if not profile:
            continue

        bulk.append(
            UpdateOne(
                filter={"_id": product["_id"]},
                update={"$set": {"relatedCategory": profile["relatedCategory"], "dateModified": get_now().isoformat()}}
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
    await migrate_categories()
    await migrate_profiles()
    await migrate_product_classification()
    await migrate_products_related_category()


def main():
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_mongo())
    loop.run_until_complete(migrate())


if __name__ == '__main__':
    main()
