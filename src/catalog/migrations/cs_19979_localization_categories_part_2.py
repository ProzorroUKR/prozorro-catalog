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

PARENT_CATEGORY_CLASSIFICATION_ID = "43410000-0"

CATEGORY_MAPPING = {
    "Взуття різне, крім спортивного та захисного": "18810000-0",
    "Військова форма одягу": "35811300-5",
    "Водонепроникний одяг": "18221000-4",
    "Головні убори": "18443300-9",
    "Деталі трубопроводів безшовні, приварні, умовним діаметром від 50 до 300":  "44167000-8",
    "Конструкції та їх частини: металоконструкції опор ліній електропередач": "44210000-5",
    "Літній одяг": "18132000-3",
    "Ліфти": "42410000-3",
    "Насоси для пожежогасіння": "42122110-4",
    "Облаштування для доріг: металеві бар’єрні огорожі та шумозахисні": "34920000-2",
    "Огорожі": "34928200-0",
    "Однострій (формений одяг) поліцейських": "35811200-4",
    "Підшипники": "34320000-6",
    "Світлофори дорожні": "34996100-6",
    "Спеціальний та робочий одяг": "18130000-9",
    "Спідня білизна": "18310000-5",
    "Трактори": "16700000-2",
    "Труби сталеві зварні діаметром 406-1422 мм": "44163100-1",
    "Формений одяг служби цивільного захисту ": "35810000-5",
    "Футболки та сорочки": "18330000-1",
    "Білизна постільна": "39512000-4",
    "Кабелі": "44321000-6",
    "Ковдри": "39511100-8",
    "Освітлювальна техніка": "31520000-7",
    "Рукавички (окрім тактичних)": "18424000-7",
    "Рюкзаки": "18931100-5",
    "Спальні мішки": "39522540-4",
}


async def migrate():
    logger.info("Start migration")
    counter = 0

    category_collection = get_category_collection()

    async with transaction_context_manager() as session:
        localization_category = await category_collection.find_one(
            filter={"classification.id": PARENT_CATEGORY_CLASSIFICATION_ID},
        )

        for title, class_id in CATEGORY_MAPPING.items():
            category_data = deepcopy(localization_category)
            category_data.update({
                "_id": uuid4().hex,
                "title": title,
                "classification": {
                    "id": class_id,
                    "scheme": "ДК021",
                    "description": DK_CODES[class_id]
                },
                "dateModified": get_now().isoformat(),
            })

            try:
                await category_collection.insert_one(category_data, session=session)
                counter += 1
                logger.info(
                    f"Created category: "
                    f"{category_data['_id']} - {category_data['classification']['id']} - {category_data['title']}"
                )
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
