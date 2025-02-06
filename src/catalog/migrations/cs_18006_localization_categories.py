import asyncio
from copy import deepcopy
from uuid import uuid4
from decimal import Decimal

import logging
import sentry_sdk

from catalog.db import (
    init_mongo,
    transaction_context_manager,
    get_category_collection,
    get_profiles_collection,
)
from catalog.utils import get_now
from catalog.logging import setup_logging
from catalog.settings import SENTRY_DSN

logger = logging.getLogger(__name__)


CATEGORY_ID = "99999999-919912-02426097"


PROFILES_IDS = [
    "999937-99999999-919998-02426097",
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
    "999940-99999999-919998-02426097",
    "999983-99999999-919998-02426097",
    "999959-99999999-919998-02426097",
    "999990-99999999-919998-02426097",
    "999991-99999999-919998-02426097",
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
    "999935-99999999-919998-02426097"
]


def update_criteria(criteria):
    changed = False
    for criterion in criteria:
        for rg in criterion.get("requirementGroups", ""):
            for req in rg.get("requirements", ""):
                if req.get("unit") and req.get("dataType") in ("boolean", "string"):
                    changed = True
                    req.pop("unit")
    if changed:
        return criteria


async def migrate():
    logger.info("Start migration")
    counter = 0

    category_collection = get_category_collection()
    profiles_collection = get_profiles_collection()

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

        async for profile in profiles_collection.find(
            {"_id": {"$in": PROFILES_IDS}},
            {"unit": 1, "title": 1, "classification": 1},
        ):
            category_data = deepcopy(localization_category)
            category_data.update(profile)

            for c in category_data["criteria"]:
                if c["classification"]["id"] == "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL":
                    c["requirementGroups"][0]["requirements"][0]["minValue"] = 25.0
                    break

            category_data["_id"] = uuid4().hex
            category_data["status"] = "active"
            category_data["dateModified"] = get_now().isoformat()

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
