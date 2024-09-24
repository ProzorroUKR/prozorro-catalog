from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_17668_standartize_requirements import (
    migrate,
)
from tests.integration.conftest import api, db, get_fixture_json


# якщо є expectedValue і minValue або maxValue -> видаляємо minValue і maxValue
# якщо є expectedValues і minValue або maxValue -> видаляємо minValue і maxValue
async def test_requirements_with_both_fields(db, api):
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
                        "title": "Відповідність ДСТУ 5028",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [True, False],
                        "minValue": True
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["FOO", "BAR"],
                        "maxValue": "foobar"
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": "FOO",
                        "minValue": "foobar"
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert "minValue" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][0]
    assert "maxValue" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][1]
    assert "minValue" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][2]


# dataType dataType = "boolean"
#
# якщо expectedValues = [true] -> dataType = "boolean", expectedValue = true
# якщо expectedValues = [false] -> dataType = "boolean", expectedValue = false
# якщо expectedValues = [true, false] -> dataType = "boolean", expectedValue = null
# якщо expectedValues = ["some_string"] -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValues = [0, 10, 20] -> dataType = "string", expectedValues = ["0", "10", "20"]
# якщо expectedValues = [0.0, 10.5, 20.9] -> dataType = "string", expectedValues = ["0.0", "10.5", "20.9"]
# якщо expectedValue = "some_string" -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = 10 -> dataType = "string", expectedValues = ["10"]
# якщо expectedValue = 10.5 -> dataType = "string", expectedValues = ["10.5"]

async def test_requirements_boolean(db, api):
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
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [True],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [False]
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [True, False],
                        "expectedMinItems": 1,
                        "expectedMaxItems": 1
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [False, True]
                    }, {
                        "title": "Xарактеристика №5",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0, 10, 20]
                    }, {
                        "title": "Xарактеристика №6",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["some_string"]
                    }, {
                        "title": "Xарактеристика №7",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0.0, 10.5, 20.9]
                    },  {
                        "title": "Xарактеристика №8",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": "some_string"
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10,
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "boolean",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5,
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    product_1 = deepcopy(get_fixture_json("product"))
    product_1["_id"] = uuid4().hex
    product_1["relatedCategory"] = category["_id"]
    product_1["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "values": [True]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": False
        },
        {
            "requirement": "Xарактеристика №3",
            "value": False
        },
        {
            "requirement": "Xарактеристика №5",
            "values": [10]
        },
        {
            "requirement": "Xарактеристика №6",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 10.5
        }, {
            "requirement": "Xарактеристика №10",
            "values": [10.5]
        }
    ]
    await db.products.insert_one(product_1)

    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][0] == {
        "title": "Xарактеристика №1",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": True
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][1] == {
        "title": "Xарактеристика №2",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": False
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][2] == {
        "title": "Xарактеристика №3",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][3] == {
        "title": "Xарактеристика №4",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][4] == {
        "title": "Xарактеристика №5",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0", "10", "20"],
        "expectedMinItems": 1
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][5] == {
        "title": "Xарактеристика №6",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][6] == {
        "title": "Xарактеристика №7",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0.0", "10.5", "20.9"],
        "expectedMinItems": 1
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][7] == {
        "title": "Xарактеристика №8",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1

    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][8] == {
        "title": "Xарактеристика №9",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10"],
        "expectedMinItems": 1
    }
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][9] == {
        "title": "Xарактеристика №10",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10.5"],
        "expectedMinItems": 1
    }

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["requirementResponses"] == [
        {
            "requirement": "Xарактеристика №1",
            "values": [True]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": False
        },
        {
            "requirement": "Xарактеристика №3",
            "value": False
        },
        {
            "requirement": "Xарактеристика №5",
            "values": ["10"]
        },
        {
            "requirement": "Xарактеристика №6",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №7",
            "value": "10.5"
        }, {
            "requirement": "Xарактеристика №10",
            "values": ["10.5"]
        }
    ]


#dataType dataType = "string"

# якщо expectedValues = [true, false] -> dataType = "string", expectedValues = ["true", "false"]
# якщо expectedValues = [0, 10, 20] -> dataType = "string", expectedValues = ["0", "10", "20"]
# якщо expectedValue = "some_string" -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = true -> dataType = "string", expectedValues = ["true"]
# якщо expectedValue = 10 -> dataType = "string", expectedValues = ["10"]
# якщо expectedValue = 10.5 -> dataType = "string", expectedValues = ["10.5"]
# якщо minValue = 10 -> dataType = "number", minValue = 10.0
# якщо maxValue = 20 -> dataType = "number", maxValue = 20.0
# якщо minValue = 10.5 -> dataType = "number", minValue = 10.0
# якщо maxValue = 20.5 -> dataType = "number", maxValue = 20.0
async def test_requirements_string(db, api):
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
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [True, False],
                        "expectedMinItems": 1,
                        "unit": {
                            "code": "CMT",
                            "name": "см"
                        },
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0, 10, 20]
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["some_string"],
                        "expectedMinItems": 1,
                        "expectedMaxItems": 1
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": "some_string"
                    }, {
                        "title": "Xарактеристика №5",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": True
                    }, {
                        "title": "Xарактеристика №6",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10
                    }, {
                        "title": "Xарактеристика №7",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5
                    },  {
                        "title": "Xарактеристика №8",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "maxValue": 10.5,
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0.5, 10.5, 20]
                    }, {
                        "title": "Xарактеристика №11",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10.5,
                        "maxValue": 13.5
                    }, {
                        "title": "Xарактеристика №12",
                        "dataType": "string",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    product_1 = deepcopy(get_fixture_json("product"))
    product_1["_id"] = uuid4().hex
    product_1["relatedCategory"] = category["_id"]
    product_1["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "values": [True]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": 10
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": True
        },
        {
            "requirement": "Xарактеристика №6",
            "value": 10
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 9.2
        }, {
            "requirement": "Xарактеристика №10",
            "values": [10.5]
        }
    ]
    await db.products.insert_one(product_1)

    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"] == [{
        "title": "Xарактеристика №1",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True", "False"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №2",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0", "10", "20"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №3",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1
    }, {
        "title": "Xарактеристика №4",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №5",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №6",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №7",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10.5"],
        "expectedMinItems": 1
    },  {
        "title": "Xарактеристика №8",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №9",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10.5"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №10",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0.5", "10.5", "20"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №11",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["10.5", "13.5"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №12",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
    }]

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["requirementResponses"] ==  [
        {
            "requirement": "Xарактеристика №1",
            "values": ["True"]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": "10"
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": "True"
        },
        {
            "requirement": "Xарактеристика №6",
            "value": "10"
        },
        {
            "requirement": "Xарактеристика №7",
            "value": "9.2"
        }, {
            "requirement": "Xарактеристика №10",
            "values": ["10.5"]
        }
    ]


# dataType dataType = "number"
#
# якщо expectedValues = [true, false] -> dataType = "string", expectedValues = ["true", "false"]
# якщо expectedValues = [0, 10, 20] -> dataType = "string", expectedValues = ["0", "10", "20"]
# якщо expectedValues = ["some_string"] -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = "some_string" -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = true -> dataType = "string", expectedValues = ["true"]
# якщо expectedValue = 10 -> dataType = "number", expectedValues = 10.0
# якщо minValue = 10 -> dataType = "number", minValue = 10.0
# якщо maxValue = 20 -> dataType = "number", maxValue = 20.0
# якщо dataType = "number" і відсутні одночасно expectedValue, expectedValues, minValue, maxValue - minValue = min (value усіх товарів)

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
                        "expectedValues": [True, False],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0, 10, 20]
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["some_string"],
                        "expectedMinItems": 1,
                        "expectedMaxItems": 1
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": "some_string"
                    }, {
                        "title": "Xарактеристика №5",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": True,
                        "unit": {
                            "code": "CMT",
                            "name": "см"
                        },
                    }, {
                        "title": "Xарактеристика №6",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10,
                        "unit": {
                            "code": "CMT",
                            "name": "см"
                        },
                    }, {
                        "title": "Xарактеристика №7",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5
                    },  {
                        "title": "Xарактеристика №8",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "maxValue": 10.5,
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0.5, 10.5, 20]
                    }, {
                        "title": "Xарактеристика №11",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10,
                        "maxValue": 20
                    }, {
                        "title": "Xарактеристика №12",
                        "dataType": "number",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    product_1 = deepcopy(get_fixture_json("product"))
    product_1["_id"] = uuid4().hex
    product_1["relatedCategory"] = category["_id"]
    product_1["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "values": [True]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": 10
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": True
        },
        {
            "requirement": "Xарактеристика №6",
            "value": 10
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 9.2
        }, {
            "requirement": "Xарактеристика №10",
            "values": [10.5]
        },
        {
            "requirement": "Xарактеристика №12",
            "value": 12
        }
    ]
    await db.products.insert_one(product_1)

    product_2 = deepcopy(get_fixture_json("product"))
    product_2["_id"] = uuid4().hex
    product_2["relatedCategory"] = category["_id"]
    product_2["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №12",
            "values": [11]
        },
    ]
    await db.products.insert_one(product_2)

    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"] == [{
        "title": "Xарактеристика №1",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True", "False"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №2",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0", "10", "20"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №3",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1
    }, {
        "title": "Xарактеристика №4",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №5",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №6",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": 10.0,
        "unit": {
            "code": "CMT",
            "name": "см"
        },
    }, {
        "title": "Xарактеристика №7",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": 10.5
    },  {
        "title": "Xарактеристика №8",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 10.0
    }, {
        "title": "Xарактеристика №9",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "maxValue": 10.5
    }, {
        "title": "Xарактеристика №10",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0.5", "10.5", "20"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №11",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 10.0,
        "maxValue": 20.0
    }, {
        "title": "Xарактеристика №12",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 11.0
    }]

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["requirementResponses"] ==  [
        {
            "requirement": "Xарактеристика №1",
            "values": ["True"]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": "10"
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": "True"
        },
        {
            "requirement": "Xарактеристика №6",
            "value": 10.0
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 9.2
        }, {
            "requirement": "Xарактеристика №10",
            "values": ["10.5"]
        }, {
            "requirement": "Xарактеристика №12",
            "value": 12.0
        }
    ]


# dataType dataType = "integer"
#
# якщо expectedValues = [true, false] -> dataType = "string", expectedValues = ["true", "false"]
# якщо expectedValues = [0, 10, 20] -> dataType = "string", expectedValues = ["0", "10", "20"]
# якщо expectedValues = ["some_string"] -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = "some_string" -> dataType = "string", expectedValues = ["some_string"]
# якщо expectedValue = true -> dataType = "string", expectedValues = ["true"]
# якщо expectedValue = 10.5 -> dataType = "number", expectedValue = 10.5
# якщо minValue = 10.5 -> dataType = "number", minValue = 10.5
# якщо maxValue = 20.5 -> dataType = "number", maxValue = 20.5
# якщо dataType = "integer" і відсутні одночасно expectedValue, expectedValues, minValue, maxValue - minValue = min (value усіх товарів)
async def test_requirements_integer(db, api):
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
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [True, False],
                        "expectedMinItems": 1
                    }, {
                        "title": "Xарактеристика №2",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0, 10, 20]
                    }, {
                        "title": "Xарактеристика №3",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": ["some_string"],
                        "expectedMinItems": 1,
                        "expectedMaxItems": 1
                    }, {
                        "title": "Xарактеристика №4",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": "some_string"
                    }, {
                        "title": "Xарактеристика №5",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": True
                    }, {
                        "title": "Xарактеристика №6",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10
                    }, {
                        "title": "Xарактеристика №7",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValue": 10.5
                    },  {
                        "title": "Xарактеристика №8",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10.5
                    }, {
                        "title": "Xарактеристика №9",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "maxValue": 20.5,
                    }, {
                        "title": "Xарактеристика №10",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "expectedValues": [0.5, 10.5, 20]
                    }, {
                        "title": "Xарактеристика №11",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        "minValue": 10.0,
                        "maxValue": 20
                    }, {
                        "title": "Xарактеристика №12",
                        "dataType": "integer",
                        "id": "8726f95aeb1d4b289d6c1a5a07271c93"
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    product_1 = deepcopy(get_fixture_json("product"))
    product_1["_id"] = uuid4().hex
    product_1["relatedCategory"] = category["_id"]
    product_1["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "values": [True]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": 10
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": True
        },
        {
            "requirement": "Xарактеристика №6",
            "value": 10.5
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 9.2
        }, {
            "requirement": "Xарактеристика №10",
            "values": [10.5]
        },
        {
            "requirement": "Xарактеристика №12",
            "value": 12
        }
    ]
    await db.products.insert_one(product_1)

    product_2 = deepcopy(get_fixture_json("product"))
    product_2["_id"] = uuid4().hex
    product_2["relatedCategory"] = category["_id"]
    product_2["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №12",
            "values": [11]
        },
    ]
    await db.products.insert_one(product_2)

    await migrate()

    category_data = await db.category.find_one({"_id": category["_id"]})
    assert category_data["criteria"][0]["requirementGroups"][0]["requirements"] == [{
        "title": "Xарактеристика №1",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True", "False"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №2",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0", "10", "20"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №3",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1
    }, {
        "title": "Xарактеристика №4",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["some_string"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №5",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["True"],
        "expectedMinItems": 1,
    }, {
        "title": "Xарактеристика №6",
        "dataType": "integer",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": 10,
    }, {
        "title": "Xарактеристика №7",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValue": 10.5
    },  {
        "title": "Xарактеристика №8",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 10.5
    }, {
        "title": "Xарактеристика №9",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "maxValue": 20.5
    }, {
        "title": "Xарактеристика №10",
        "dataType": "string",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": ["0.5", "10.5", "20"],
        "expectedMinItems": 1
    }, {
        "title": "Xарактеристика №11",
        "dataType": "number",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 10.0,
        "maxValue": 20.0
    }, {
        "title": "Xарактеристика №12",
        "dataType": "integer",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "minValue": 11
    }]

    product_data = await db.products.find_one({"_id": product_1["_id"]})
    assert product_data["requirementResponses"] ==  [
        {
            "requirement": "Xарактеристика №1",
            "values": ["True"]
        },
        {
            "requirement": "Xарактеристика №2",
            "value": "10"
        },
        {
            "requirement": "Xарактеристика №3",
            "value": "some_string"
        },
        {
            "requirement": "Xарактеристика №5",
            "value": "True"
        },
        {
            "requirement": "Xарактеристика №6",
            "value": 10.5
        },
        {
            "requirement": "Xарактеристика №7",
            "value": 9.2
        }, {
            "requirement": "Xарактеристика №10",
            "values": ["10.5"]
        }, {
            "requirement": "Xарактеристика №12",
            "value": 12
        }
    ]