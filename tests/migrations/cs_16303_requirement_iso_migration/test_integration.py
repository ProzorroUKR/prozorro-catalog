from copy import deepcopy
from uuid import uuid4

from catalog.migrations.cs_16303_requirement_iso_migration import (
    CATEGORY_IDS,
    migrate,
)
from tests.integration.conftest import api, db, get_fixture_json


async def test_migrate_iso_requirements(db, api):
    category = deepcopy(get_fixture_json('category'))
    category["_id"] = CATEGORY_IDS[-1]
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
                        "expectedMinItems": 1,
                        "expectedMaxItems": 1,
                    }]
                }
            ]
        }
    ]
    await db.category.insert_one(category)

    category_another_req = deepcopy(category)
    category_another_req["_id"] = CATEGORY_IDS[-2]
    category_another_req["criteria"][0]["requirementGroups"][0]["requirements"] = [{
        "title": "Відповідність ГОСТ 5028",
        "dataType": "boolean",
        "id": "8726f95aeb1d4b289d6c1a5a07271c93",
        "expectedValues": [False]
    }, {
        "title": "Категорія",
        "dataType": "string",
        "expectedValues": [
            "Відбірні (XL)",
            "Вища (L)",
            "Перша (М)",
            "Друга (S)"
        ],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
        "id": "0cd12ae1084640dbbff74a93e6b2dc92",
    }]
    await db.category.insert_one(category_another_req)

    product_1 = deepcopy(get_fixture_json("product"))
    product_1["_id"] = uuid4().hex
    product_1["relatedCategory"] = CATEGORY_IDS[-1]
    product_1["requirementResponses"] = [
        {
            "requirement": "Відповідність ДСТУ 5028",
            "values": ["Так"]
        }
    ]
    await db.products.insert_one(product_1)

    product_2 = deepcopy(get_fixture_json("product"))
    product_2["_id"] = uuid4().hex
    product_2["relatedCategory"] = CATEGORY_IDS[-1]
    product_2["requirementResponses"] = [
        {
            "requirement": "Відповідність ДСТУ 5028",
            "values": ["Hi"]
        }
    ]
    await db.products.insert_one(product_2)

    product_3 = deepcopy(get_fixture_json("product"))
    product_3["_id"] = uuid4().hex
    product_3["relatedCategory"] = CATEGORY_IDS[-2]
    product_3["requirementResponses"] = [
        {
            "requirement": "Відповідність ГОСТ 5028",
            "values": [False]
        }, {
            "requirement": "Категорія",
            "values": [
                "Відбірні (XL)",
            ]
        }
    ]
    await db.products.insert_one(product_3)

    product_4 = deepcopy(get_fixture_json("product"))
    product_4["_id"] = uuid4().hex
    product_4["relatedCategory"] = CATEGORY_IDS[-1]
    product_4["requirementResponses"] = [
        {
            "requirement": "Відповідність ДСТУ 5028",
            "values": [False]
        }
    ]
    await db.products.insert_one(product_4)

    await migrate()

    for category_obj in (category, category_another_req):
        category_data = await db.category.find_one({"_id": category_obj["_id"]})
        assert "expectedValues" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][0]
        assert "expectedMinItems" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][0]
        assert "expectedMaxItems" not in category_data["criteria"][0]["requirementGroups"][0]["requirements"][0]
        assert category_data["criteria"][0]["requirementGroups"][0]["requirements"][0]["expectedValue"] is True

    for product in (product_1, product_2, product_3, product_4):
        product_data = await db.products.find_one({"_id": product["_id"]})
        assert product_data["requirementResponses"][0]["value"] is True
        assert "values" not in product_data["requirementResponses"][0]
