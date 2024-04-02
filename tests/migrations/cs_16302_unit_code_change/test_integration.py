from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_16302_update_unit_code_for_specific_owner import (
    OWNER,
    PREVIOUS_UNIT_CODE,
    migrate,
    NEW_UNIT_DATA,
)
from tests.integration.conftest import db, get_fixture_json


async def test_migrate_unit_for_specific_owner(db):
    category = deepcopy(get_fixture_json('category'))
    category["unit"]["code"] = PREVIOUS_UNIT_CODE
    category["access"] = {"owner": OWNER}
    category["_id"] = uuid4().hex
    await db.category.insert_one(category)

    category_another_unit = deepcopy(get_fixture_json('category'))
    category_another_unit["access"] = {"owner": OWNER}
    category_another_unit["_id"] = uuid4().hex
    await db.category.insert_one(category_another_unit)

    category_another_owner = deepcopy(get_fixture_json('category'))
    category_another_owner["unit"]["code"] = PREVIOUS_UNIT_CODE
    category_another_owner["_id"] = uuid4().hex
    await db.category.insert_one(category_another_owner)

    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
    profile["unit"] = {"code": PREVIOUS_UNIT_CODE}
    profile["access"] = {"owner": OWNER}
    await db.profiles.insert_one(profile)

    profile_another_unit = deepcopy(get_fixture_json('profile'))
    profile_another_unit["access"] = {"owner": OWNER}
    profile_another_unit["unit"] = {"code": "PK"}
    profile_another_unit["_id"] = uuid4().hex
    await db.profiles.insert_one(profile_another_unit)

    profile_another_owner = deepcopy(get_fixture_json('profile'))
    profile_another_owner["unit"] = {"code": PREVIOUS_UNIT_CODE}
    profile_another_owner["_id"] = uuid4().hex
    await db.profiles.insert_one(profile_another_owner)

    await migrate()
    category_1 = await db.category.find_one({"_id": category["_id"]})
    assert category_1["unit"] == NEW_UNIT_DATA

    category_2 = await db.category.find_one({"_id": category_another_unit["_id"]})
    assert category_2["unit"] != NEW_UNIT_DATA

    category_3 = await db.category.find_one({"_id": category_another_owner["_id"]})
    assert category_3["unit"]["code"] == PREVIOUS_UNIT_CODE

    profile_1 = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_1["unit"] == NEW_UNIT_DATA

    profile_2 = await db.profiles.find_one({"_id": profile_another_unit["_id"]})
    assert profile_2["unit"] != NEW_UNIT_DATA

    profile_3 = await db.profiles.find_one({"_id": profile_another_owner["_id"]})
    assert profile_3["unit"]["code"] == PREVIOUS_UNIT_CODE
