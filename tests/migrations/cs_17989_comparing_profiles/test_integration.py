from copy import deepcopy
from uuid import uuid4

from catalog.migrations.comparing_profiles_with_categories import (
    migrate_profiles,
)
from tests.integration.conftest import api, db, get_fixture_json


async def test_requirements_number(db, api):
    category = deepcopy(get_fixture_json('category'))
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
                        "expectedValue": 10.0
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 1.0
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 20
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10
                    }, {
                        "title": "Xарактеристика №5",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "maxValue": 15,
                        "minValue": 0
                    }, {
                        "title": "Xарактеристика №7",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10
                    }, {
                        "title": "Xарактеристика №8",
                        "dataType": "boolean",
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["foo"],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["foo"],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №11",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["foo"],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №12",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10,
                    }, {
                        "title": "Xарактеристика №13",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 1,
                    }, {
                        "title": "Xарактеристика №14",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5,
                    }, {
                        "title": "Xарактеристика №15",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10,
                        "maxValue": 20
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
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
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["10"]
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["10", "20"]
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["10"]
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["dsd"]
                    }, {
                        "title": "Xарактеристика нема такої",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["10"]
                    }, {
                        "title": "Xарактеристика №8",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["dsd"],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": True,
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 0,
                        "maxValue": 10
                    }, {
                        "title": "Xарактеристика №11",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 5
                    }, {
                        "title": "Xарактеристика №12",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10,
                    }, {
                        "title": "Xарактеристика №13",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 0,
                    }, {
                        "title": "Xарактеристика №14",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5,
                    }, {
                        "title": "Xарактеристика №15",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10.0,
                        "maxValue": 20.0
                    }]
                }
            ]
        }
    ]
    await db.profiles.insert_one(profile)

    await migrate_profiles()

    profile_data = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_data["criteria"][0]["requirementGroups"][0]["requirements"] == [
        {
            "title": "Xарактеристика №1",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10.0
        }, {
            "title": "Xарактеристика №2",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["10", "20"]
        }, {
            "title": "Xарактеристика №3",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10
        }, {
            "title": "Xарактеристика №4",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["dsd"]
        }, {
            "title": "Xарактеристика нема такої",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["10"]
        }, {
            "title": "Xарактеристика №8",
            "dataType": "boolean",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        }, {
            "title": "Xарактеристика №9",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["True"],
            "expectedMinItems": 1
        }, {
            "title": "Xарактеристика №10",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["0", "10"],
            "expectedMinItems": 1
        }, {
            "title": "Xарактеристика №11",
            "dataType": "string",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValues": ["5"],
            "expectedMinItems": 1
        }, {
            "title": "Xарактеристика №12",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10,
        }, {
            "title": "Xарактеристика №13",
            "dataType": "integer",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "minValue": 0,
        }, {
            "title": "Xарактеристика №14",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "expectedValue": 10.5,
        }, {
            "title": "Xарактеристика №15",
            "dataType": "number",
            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
            "minValue": 10.0,
            "maxValue": 20.0
        }
    ]
