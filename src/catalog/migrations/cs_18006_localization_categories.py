import asyncio
import standards
from copy import deepcopy
from uuid import uuid4

import logging
import sentry_sdk

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
)
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)

DK_CODES = standards.load("classifiers/dk021_uk.json")

CATEGORY_ID = "99999999-919912-02426097"

CATEGORY_MAPPING = {
    "31170000-8": "Трансформатори",
    "31710000-6": "Електронне обладнання (конденсатори)",
    "34114122-0": "Транспортні засоби для перевезення пацієнтів",
    "34121000-1": "Міські та туристичні автобуси",
    "34130000-7": "Мототранспортні вантажні засоби (автоцистерни, самоскиди та фургони)",
    "34140000-0": "Великовантажні мототранспортні засоби (від автокранів, сміттєвозів до єлектробусів)",
    "34210000-2": "Кузови транспортних засобів",
    "34220000-5": "Причепи, напівпричепи та пересувні контейнери",
    "34610000-6": "Залізничні локомотиви та тендери",
    "34620000-9": "Рейковий рухомий склад (засоби для ремонту, вантажні та пасажирські вагони, тролейбуси)",
    "34640000-5": "Самохідні частини",
    "34710000-7": "Вертольоти, літаки, космічні та інші літальні апарати з двигуном",
    "34731000-0": "Частини повітряних літальних апаратів",
    "35610000-3": "Військові літаки (навчально-тренувальні літаки та пошуково-рятувальні вертольоти)",
    "42110000-3": "Турбіни та мотори (парові, гідравлічні та спеціального призначення)",
    "42120000-6": "Насоси",
    "42990000-2": "Машини спеціального призначення різні",
    "43120000-0": "Врубові та тунелепрохідні, бурильні чи прохідницькі машини для добування вугілля чи гірських порід",
    "43210000-8": "Машини для земляних робіт",
    "43250000-0": "Фронтальні ковшові навантажувачі",
    "43260000-3": "Механічні лопати, екскаватори та ковшові навантажувачі, гірнича техніка",
    "43410000-0": "Машини для обробки мінералів",
}


async def migrate():
    logger.info("Start migration")
    counter = 0

    category_collection = get_category_collection()

    MARKET_ADMINISTRATOR_UPDATE_DATA = {
        "address": {
            "countryName": "Україна",
            "locality": "Київ",
            "postalCode": "01601",
            "region": "м. Київ",
            "streetAddress": "Бульварно-Кудрявська, 22"
        },
        "contactPoint": {
            "email": "a.illiustrova@prozorro.ua",
            "telephone": "+380675554355",
            "name_uk": "Анастасія Іллюстрова"
        },
        "identifier": {
            "id": "02426097",
            "scheme": "UA-EDR",
            "legalName": "ДЕРЖАВНА УСТАНОВА \"Прозорро\""
        },
        "name": "ДЕРЖАВНА УСТАНОВА \"Прозорро\"",
    }

    async with transaction_context_manager() as session:
        localization_category = await category_collection.find_one_and_update(
            filter={"_id": CATEGORY_ID},
            update={"$set": {"status": "hidden"}},
        )
        localization_category.pop("additionalClassifications", None)
        localization_category["marketAdministrator"].update(MARKET_ADMINISTRATOR_UPDATE_DATA)

        for class_id, title in CATEGORY_MAPPING.items():
            category_data = deepcopy(localization_category)
            category_data.update({
                "_id": uuid4().hex,
                "unit": {
                    "code": "H87",
                    "name": "штуки"
                },
                "title": title,
                "classification": {
                    "id": class_id,
                    "scheme": "ДК021",
                    "description": DK_CODES[class_id]
                },
                "status": "active",
                "dateModified": get_now().isoformat(),
            })

            for c in category_data["criteria"]:
                if c["classification"]["id"] == "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL":
                    c["requirementGroups"][0]["requirements"][0]["minValue"] = 25.0
                    break

            try:
                await category_collection.insert_one(category_data, session=session)
                counter += 1
                logger.info(f"Created category: {category_data['_id']} - {category_data['classification']['id']}")
            except Exception as e:
                logger.error(f"Category {category_data['_id']} not created, cause error: {e}")
                raise e

    logger.info(f"Finished. Processed {counter} created categories")
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
