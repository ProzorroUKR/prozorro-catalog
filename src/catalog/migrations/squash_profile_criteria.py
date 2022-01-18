import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4
import logging
from catalog.settings import MONGODB_URI, DB_NAME, READ_PREFERENCE, WRITE_CONCERN, READ_CONCERN
from catalog.utils import get_now

CLIENT = AsyncIOMotorClient(MONGODB_URI)
DB = CLIENT.get_database(
    DB_NAME,
    read_preference=READ_PREFERENCE,
    write_concern=WRITE_CONCERN,
    read_concern=READ_CONCERN,
)
collection = DB.profiles
logger = logging.getLogger(__name__)


def create_new_criteria(old_criteria: list, new_criterion: dict) -> list:
    if not old_criteria:
        return []
    new_criterion["title"] = "Технічні характеристики предмета закупівлі"
    new_criterion["code"] = old_criteria[0]["code"]
    new_rg = {"description": "Технічні характеристики", "id": uuid4().hex}
    new_reqs = []

    for old_criterion in old_criteria:
        for rg in old_criterion["requirementGroups"]:
            new_req = rg["requirements"][0]

            if rg["requirements"] == [new_req]:
                new_reqs.append(new_req)
                continue

            if "expectedValue" not in new_req:
                raise ValueError(f"No expectedValue in {old_criterion['id']}")

            new_req["anyOf"] = []
            for requirement in rg["requirements"]:
                if "expectedValue" not in requirement:
                    raise ValueError(f"No expectedValue in criterion {old_criterion['id']}")
                new_req["anyOf"].append(requirement.pop("expectedValue"))
            new_reqs.append(new_req)

    new_rg["requirements"] = new_reqs
    new_criterion["requirementGroups"] = [new_rg]
    return [new_criterion]


async def migrate():
    logger.info("Start migration")
    counter = 0
    async for profile in collection.find({}, {"criteria": 1, "title": 1}):
        counter += 1
        new_criterion = {"id": uuid4().hex, "description": profile["title"]}
        try:
            new_criteria = create_new_criteria(profile["criteria"], new_criterion)
        except ValueError as e:
            logger.warning(f"Failed to modify {profile['_id']}, {str(e)}")
        else:
            now = get_now().isoformat()
            await collection.update_one(
                {"_id": profile["_id"]},
                {"$set": {"criteria": new_criteria, "dateModified": now}}
            )
        if counter % 500 == 0:
            logger.info(f"Processed {counter} records")
    logger.info(f"Finished. Processed {counter} records")


if __name__ == '__main__':
    from catalog.logging import setup_logging
    from catalog.settings import SENTRY_DSN
    import sentry_sdk

    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(migrate())
