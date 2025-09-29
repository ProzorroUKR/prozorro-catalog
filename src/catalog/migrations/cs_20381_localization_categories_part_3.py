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
    "Одноразові рукавички": "18424300-0",
    "Хірургічні рукавички": "33141420-0",
    "Мережеві кабелі": "31310000-2",
    "Електророзподільні кабелі": "31320000-5",
    "Коаксіальні кабелі":  "31330000-8",
    "Телекомунікаційні кабелі": "32521000-1",
    "Оптоволоконні кабелі": "32562000-0",
    "Комунікаційні кабелі": "32572000-3",
    "Кабелі для передачі даних": "32581000-9",
    "Телефонні кабелі": "32551000-0",
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
