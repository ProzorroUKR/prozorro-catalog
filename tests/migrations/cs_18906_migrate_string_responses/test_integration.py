from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_18906_migrate_string_responses import (
    migrate,
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
                    "requirements": [
                        {
                            "title": "Xарактеристика №1",
                            "dataType": "string",
                            "expectedVales": ["foo", "bar"],
                            "expectedMinItems": 1,
                            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                        }, {
                            "title": "Xарактеристика №2",
                            "dataType": "string",
                            "id": "8726f95aeb1d4b289d6c1a5a07271c93",
                            "expectedValues": ["Так", "Hi"]
                        }
                    ]
                }
            ]
        }
    ]
    await db.category.insert_one(category)
    product = deepcopy(get_fixture_json("product"))
    product["_id"] = uuid4().hex
    product["relatedCategory"] = category["_id"]
    product["dateModified"] = "2025-02-02T00:00:00+02:00"
    product["requirementResponses"] = [
        {
          "requirement": "Xарактеристика №1",
          "values": ["foo", "bar"]
        },
        {
          "requirement": "Xарактеристика №2",
          "value": "Так"
        },
    ]
    await db.products.insert_one(product)

    product_2 = deepcopy(product)
    product_2["_id"] = uuid4().hex
    product_2["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "value": "foo"
        },
        {
            "requirement": "Xарактеристика №2",
            "values": ["Hi"]
        },
    ]
    await db.products.insert_one(product_2)

    product_3 = deepcopy(product)
    product_3["_id"] = uuid4().hex
    product_3["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №2",
            "values": ["Hi"]
        },
    ]
    await db.products.insert_one(product_3)

    product_4 = deepcopy(product)
    product_4["_id"] = uuid4().hex
    product_4["requirementResponses"] = [
        {
            "requirement": "Xарактеристика №1",
            "values": ["foo", "bar"]
        },
    ]
    await db.products.insert_one(product_4)

    await migrate()

    product_data = await db.products.find_one({"_id": product["_id"]})
    assert product_data["requirementResponses"] == [
        {
          "requirement": "Xарактеристика №1",
          "values": ["foo", "bar"]
        },
        {
          "requirement": "Xарактеристика №2",
          "values": ["Так"]
        },
    ]
    assert product_data["dateModified"] != product["dateModified"]

    product_data_2 = await db.products.find_one({"_id": product_2["_id"]})
    assert product_data_2["requirementResponses"] == [
        {
            "requirement": "Xарактеристика №1",
            "values": ["foo"]
        },
        {
            "requirement": "Xарактеристика №2",
            "values": ["Hi"]
        },
    ]
    assert product_data_2["dateModified"] != product_2["dateModified"]

    product_data_3 = await db.products.find_one({"_id": product_3["_id"]})
    assert product_data_3["requirementResponses"] == [
        {
            "requirement": "Xарактеристика №2",
            "values": ["Hi"]
        },
    ]
    assert product_data_3["dateModified"] == product_3["dateModified"]

    product_data_4 = await db.products.find_one({"_id": product_4["_id"]})
    assert product_data_4["requirementResponses"] == [
        {
            "requirement": "Xарактеристика №1",
            "values": ["foo", "bar"]
        },
    ]
    assert product_data_4["dateModified"] == product_4["dateModified"]
