from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_18810_data_schema_in_local_criteria import (
    migrate,
)
from catalog.settings import TECHNICAL_FEATURES_CRITERIA
from tests.integration.conftest import api, db, get_fixture_json


async def test_data_schema_for_localization_criteria(db, api):
    category = deepcopy(get_fixture_json('category'))
    category["_id"] = uuid4().hex
    category["criteria"] = deepcopy(get_fixture_json('criteria')["criteria"])
    del category["criteria"][1]["requirementGroups"][1]["requirements"][0]["dataSchema"]
    await db.category.insert_one(category)

    category_2 = deepcopy(category)
    category_2["_id"] = uuid4().hex
    category_2["criteria"][1]["requirementGroups"][1]["requirements"][0]["expectedValues"] = ["foo", "bar"]
    await db.category.insert_one(category_2)

    category_3 = deepcopy(category)
    category_3["_id"] = uuid4().hex
    category_3["criteria"][1]["requirementGroups"][1]["requirements"][0]["expectedValues"] = ["UA", "GB"]
    await db.category.insert_one(category_3)

    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
    profile["relatedCategory"] = category["_id"]
    profile["dateModified"] = "2024-10-01T11:54:57.860085+03:00"
    profile["criteria"] = deepcopy(get_fixture_json('criteria')["criteria"])
    del profile["criteria"][1]["requirementGroups"][1]["requirements"][0]["dataSchema"]
    await db.profiles.insert_one(profile)

    profile_2 = deepcopy(profile)
    profile_2["_id"] = uuid4().hex
    profile_2["criteria"][1]["classification"]["id"] = TECHNICAL_FEATURES_CRITERIA
    await db.profiles.insert_one(profile_2)

    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][1]["requirementGroups"][1]["requirements"][0]["dataSchema"] == "ISO 3166-1 alpha-2"

    category_data_2 = await db.category.find_one({"_id": category_2["_id"]})
    assert "dataSchema" not in category_data_2["criteria"][1]["requirementGroups"][1]["requirements"][0]

    category_data_3 = await db.category.find_one({"_id": category_3["_id"]})
    assert category_data_3["criteria"][1]["requirementGroups"][1]["requirements"][0]["dataSchema"] == "ISO 3166-1 alpha-2"

    profile_data = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_data["criteria"][1]["requirementGroups"][1]["requirements"][0]["dataSchema"] == "ISO 3166-1 alpha-2"
    assert profile_data["dateModified"] != profile["dateModified"]

    profile_data_2 = await db.profiles.find_one({"_id": profile_2["_id"]})
    assert "dataSchema" not in profile_data_2["criteria"][1]["requirementGroups"][1]["requirements"][0]
    assert profile_data_2["dateModified"] == profile_2["dateModified"]
