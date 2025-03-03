from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_18855_update_unit_name_in_categories_and_profiles import (
    migrate_categories_and_profiles,
)
from tests.integration.conftest import api, db, get_fixture_json


async def test_requirements_unit(db, api):
    category = deepcopy(get_fixture_json('category'))
    category["dateModified"] = "2024-10-01T11:54:57.860085+03:00"
    category["unit"] = {
        "code": "P1",
        "name": "%"
    }
    category["criteria"] = [
        {
            "title": "Технічні характеристики предмета закупівлі",
            "description": "Яйця столові курячі",
            "id": "1f92023591bd4096aea88064eaa4b235",
            "requirementGroups": [
                {
                    "description": "Технічні характеристики",
                    "id": "f3d2b5995da042ff858a6ea7b5a1a8dd",
                    "requirements": [{
                        "title": "Xарактеристика №1",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.0,
                        "unit": {
                            "code": "CMT",
                            "name": "см"
                        }
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 1.0
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 20,
                        "unit": {
                            "code": "P1",
                            "name": "%"
                        }
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    category_2 = deepcopy(category)
    category_2["unit"] = {
        "code": "P1",
        "name": "відсоток"
    }
    category_2["_id"] = uuid4().hex
    await db.category.insert_one(category_2)

    category_3 = deepcopy(category)
    category_3.pop("unit")
    category_3.pop("criteria")
    category_3["_id"] = uuid4().hex
    await db.category.insert_one(category_3)
    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
    profile["unit"] = {
        "code": "CMT",
        "name": "см"
    }
    profile["relatedCategory"] = category["_id"]
    profile["dateModified"] = "2024-10-01T11:54:57.860085+03:00"
    profile["criteria"] = [
        {
            "title": "Технічні характеристики предмета закупівлі",
            "description": "Яйця столові курячі",
            "id": "1f92023591bd4096aea88064eaa4b235",
            "requirementGroups": [
                {
                    "description": "Технічні характеристики",
                    "id": "f3d2b5995da042ff858a6ea7b5a1a8dd",
                    "requirements": [{
                        "title": "Xарактеристика №1",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.0,
                        "unit": {
                            "code": "CMT",
                            "name": "см"
                        }
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10.0,
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 20
                    }]
                }
            ]
        }
    ]
    await db.profiles.insert_one(profile)

    profile_2 = deepcopy(profile)
    profile_2["_id"] = uuid4().hex
    profile_2["unit"] = {
        "code": "P1",
        "name": "відсоток"
    }
    profile_2["relatedCategory"] = category_2["_id"]
    profile_2["criteria"] = [
        {
            "title": "Технічні характеристики предмета закупівлі",
            "description": "Яйця столові курячі",
            "id": "1f92023591bd4096aea88064eaa4b235",
            "requirementGroups": [
                {
                    "description": "Технічні характеристики",
                    "id": "f3d2b5995da042ff858a6ea7b5a1a8dd",
                    "requirements": [{
                        "title": "Xарактеристика №1",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.0,
                        "unit": {
                            "code": "CMT",
                            "name": "сантиметр"
                        }
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 20.0,
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 20,
                        "unit": {
                            "code": "P1",
                            "name": "відсоток"
                        }
                    }]
                }
            ]
        }
    ]
    await db.profiles.insert_one(profile_2)

    await migrate_categories_and_profiles()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"] == [
        {
            "title": "Xарактеристика №1",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10.0,
            "unit": {
                "code": "CMT",
                "name": "сантиметр"
            },
        }, {
            "title": "Xарактеристика №2",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "minValue": 1.0,
        }, {
            "title": "Xарактеристика №3",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 20,
            "unit": {
                "code": "P1",
                "name": "відсоток"
            },
        }
    ]
    assert category_data["unit"] == {"code": "P1", "name": "відсоток"}
    assert category_data["dateModified"] != category["dateModified"]

    category_data_2 = await db.category.find_one({"_id": category_2["_id"]})
    assert category_data_2["unit"] == {"code": "P1", "name": "відсоток"}
    assert category_data_2["dateModified"] != category_2["dateModified"]

    category_data_3 = await db.category.find_one({"_id": category_3["_id"]})
    assert category_data_3["dateModified"] == category_3["dateModified"]

    profile_data = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_data["criteria"][0]["requirementGroups"][0]["requirements"] == [
        {
            "title": "Xарактеристика №1",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10.0,
            "unit": {
                "code": "CMT",
                "name": "сантиметр"
            },
        }, {
            "title": "Xарактеристика №2",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "minValue": 10.0,
        }, {
            "title": "Xарактеристика №3",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 20,
            "unit": {
                "code": "P1",
                "name": "відсоток"
            },
        }
    ]
    assert profile_data["unit"] == {"code": "P1", "name": "відсоток"}
    assert profile_data["dateModified"] != profile["dateModified"]

    profile_data_2 = await db.profiles.find_one({"_id": profile_2["_id"]})
    assert profile_data_2["unit"] == {"code": "P1", "name": "відсоток"}
    assert profile_data_2["criteria"][0]["requirementGroups"][0]["requirements"] == [
        {
            "title": "Xарактеристика №1",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10.0,
            "unit": {
                "code": "CMT",
                "name": "сантиметр"
            },
        }, {
            "title": "Xарактеристика №2",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "minValue": 20.0,
        }, {
            "title": "Xарактеристика №3",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 20,
            "unit": {
                "code": "P1",
                "name": "відсоток"
            },
        }
    ]
    assert profile_data_2["dateModified"] == profile_2["dateModified"]
