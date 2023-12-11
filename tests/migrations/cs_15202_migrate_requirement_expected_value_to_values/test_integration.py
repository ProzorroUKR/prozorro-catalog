from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_15202_migrate_requirement_expected_value_to_values import migrate
from tests.integration.conftest import db, get_fixture_json


async def test_migrate_value_to_values(db):
    category = deepcopy(get_fixture_json('category'))
    category["criteria"] = [
        {
            "title": "test",
            "description": "test",
            "id": "b7bcb8307a2242c28bf6eba51880a0c8",
            "requirementGroups": [
                {
                    "description": "test",
                    "id": "5221d133fa1d495fa8f241eaa58a562a",
                    "requirements": [
                        {
                            "title": "Метод аналізу 5",
                            "dataType": "integer",
                            "isArchived": False,
                            "id": "51d9181bfbee4fd588cffd71899558f1",
                            "expectedValue": 4
                        },
                        {
                            "title": "Метод аналізу 1",
                            "dataType": "integer",
                            "expectedValues": [1, 4],
                            "isArchived": False,
                            "id": "f44329f22a7f41b39350e5994018784d"
                        },
                        {
                            "title": "Метод аналізу 2",
                            "dataType": "integer",
                            "isArchived": False,
                            "id": "dde916da0d6445a09b6cf0a4fe6bf9c8",
                            "expectedValue": 1
                        },
                        {
                            "title": "Метод аналізу 3",
                            "dataType": "string",
                            "isArchived": False,
                            "id": "64e281d7a91a4c708567c71e92ba6ffa",
                            "expectedValues": ["IXA"],
                        },
                        {
                            "title": "Метод аналізу 4",
                            "dataType": "string",
                            "expectedValue": "IXA",
                            "isArchived": False,
                            "id": "7b10baf2d77047f0ad954d109080b7b5"
                        },
                        {
                            "title": "Метод аналізу 6",
                            "dataType": "string",
                            "minValue": "IXA",
                            "isArchived": False,
                            "id": "bac2c0f3aed340a796817c6eba13d708"
                        }
                    ]
                }
            ]
        }
    ]
    category["_id"] = uuid4().hex
    await db.category.insert_one(category)

    category_without_criteria = deepcopy(get_fixture_json('category'))
    category_without_criteria["criteria"] = []
    category_without_criteria["_id"] = uuid4().hex
    await db.category.insert_one(category_without_criteria)

    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
    profile["relatedCategory"] = category["_id"]
    profile["criteria"] = [
        {
            "title": "test",
            "description": "test",
            "id": "b7bcb8307a2242c28bf6eba51880a0c8",
            "requirementGroups": [
                {
                    "description": "test",
                    "id": "5221d133fa1d495fa8f241eaa58a562a",
                    "requirements": [
                        {
                            "title": "Метод аналізу 5",
                            "dataType": "integer",
                            "isArchived": False,
                            "id": "51d9181bfbee4fd588cffd71899558f1",
                            "expectedValues": [4]
                        },
                        {
                            "title": "Метод аналізу 1",
                            "dataType": "integer",
                            "expectedValues": [1, 4],
                            "isArchived": False,
                            "id": "f44329f22a7f41b39350e5994018784d"
                        },
                        {
                            "title": "Метод аналізу 2",
                            "dataType": "integer",
                            "isArchived": False,
                            "id": "dde916da0d6445a09b6cf0a4fe6bf9c8",
                            "expectedValue": 1
                        },
                        {
                            "title": "Метод аналізу 3",
                            "dataType": "string",
                            "isArchived": False,
                            "id": "64e281d7a91a4c708567c71e92ba6ffa",
                            "expectedValue": "IXA",
                        },
                        {
                            "title": "Метод аналізу 4",
                            "dataType": "string",
                            "expectedValues": ["IXA"],
                            "isArchived": False,
                            "id": "7b10baf2d77047f0ad954d109080b7b5"
                        },
                        {
                            "title": "Метод аналізу 6",
                            "dataType": "string",
                            "minValue": "IXA",
                            "isArchived": False,
                            "id": "bac2c0f3aed340a796817c6eba13d708"
                        }
                    ]
                }
            ]
        }
    ]
    await db.profiles.insert_one(profile)

    profile_without_criteria = deepcopy(get_fixture_json("profile"))
    profile_without_criteria["_id"] = uuid4().hex
    profile_without_criteria["relatedCategory"] = category_without_criteria["_id"]
    profile_without_criteria["criteria"] = []
    await db.profiles.insert_one(profile_without_criteria)

    product = deepcopy(get_fixture_json("product"))
    product["_id"] = uuid4().hex
    product["relatedCategory"] = category["_id"]
    product["relatedProfiles"] = [profile["_id"]]
    product["requirementResponses"] = [
        {
            "requirement": "Метод аналізу 1",
            "value": 1
        },
        {
            "requirement": "Метод аналізу 2",
            "values": [1, 1]
        },
        {
            "requirement": "Метод аналізу 3",
            "value": "IXA"
        },
        {
            "requirement": "Метод аналізу 4",
            "values": ["IXA"]
        }
    ]
    await db.products.insert_one(product)

    await migrate()
    category_1 = await db.category.find_one({"_id": category["_id"]})
    assert category_1["criteria"][0]["requirementGroups"][0]["requirements"][0]["expectedValues"] == [4]
    assert "expectedValue" not in category_1["criteria"][0]["requirementGroups"][0]["requirements"][0]
    assert category_1["criteria"][0]["requirementGroups"][0]["requirements"][2]["expectedValues"] == [1]
    assert "expectedValue" not in category_1["criteria"][0]["requirementGroups"][0]["requirements"][2]

    category_2 = await db.category.find_one({"_id": category_without_criteria["_id"]})
    assert category_2["criteria"] == []

    profile_1 = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_1["criteria"][0]["requirementGroups"][0]["requirements"][2]["expectedValues"] == [1]
    assert "expectedValue" not in profile_1["criteria"][0]["requirementGroups"][0]["requirements"][2]
    assert profile_1["criteria"][0]["requirementGroups"][0]["requirements"][3]["expectedValues"] == ["IXA"]
    assert "expectedValue" not in profile_1["criteria"][0]["requirementGroups"][0]["requirements"][3]

    profile_2 = await db.profiles.find_one({"_id": profile_without_criteria["_id"]})
    assert profile_2["criteria"] == []


    product_1 = await db.products.find_one({"_id": product["_id"]})
    assert product_1["requirementResponses"][0]["values"] == [1]
    assert "value" not in product_1["requirementResponses"][0]
    assert product_1["requirementResponses"][1]["values"] == [1, 1]
    assert "value" not in product_1["requirementResponses"][1]
    assert product_1["requirementResponses"][2]["values"] == ["IXA"]
    assert "value" not in product_1["requirementResponses"][2]
