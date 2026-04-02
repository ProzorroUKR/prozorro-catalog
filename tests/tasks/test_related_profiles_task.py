from copy import deepcopy

import pytest

from cron.related_profiles_task import run_task
from tests.utils import get_fixture_json


@pytest.mark.parametrize(
    ("setup_profile_data", "setup_product_data", "check_product"),
    [
        pytest.param(
            lambda init_data, profile, category: ...,
            lambda init_data, product, category: (
                init_data.update(
                    {"_id": "a" * 32, "relatedCategory": category["id"], "dateModified": "2026-01-01T00:00:00"}
                ),
                init_data.pop("requirementResponses", None),
            ),
            lambda init_data, prod: all(
                (
                    "requirementResponses" not in prod,
                    "relatedProfiles" not in prod,
                    init_data.get("dateModified") == prod.get("dateModified"),
                )
            ),
            id="product without requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: ...,
            lambda init_data, product, category: (
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"][2:],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "relatedProfiles" not in prod,
                    init_data.get("dateModified") == prod.get("dateModified"),
                )
            ),
            id="product with partial requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: (
                profile["criteria"][0]["requirementGroups"][0]["requirements"][0].update(
                    {"expectedValues": ["test_value"]}
                ),
                init_data.update({"_id": "a" * 32, "relatedCategory": category["id"], "criteria": profile["criteria"]}),
            ),
            lambda init_data, product, category: (
                product["requirementResponses"][0].update({"values": ["Одноразова2"]}),
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "relatedProfiles" not in prod,
                    init_data.get("dateModified") == prod.get("dateModified"),
                )
            ),
            id="profile requirements does not match requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: (
                profile["criteria"][0]["requirementGroups"][0]["requirements"][0].update(
                    {"expectedValues": ["test_value"]}
                ),
                init_data.update({"_id": "a" * 32, "relatedCategory": category["id"], "criteria": profile["criteria"]}),
            ),
            lambda init_data, product, category: (
                product["requirementResponses"][0].update({"values": ["test_value"]}),
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "a" * 32 in prod["relatedProfiles"],
                    init_data.get("dateModified") != prod.get("dateModified"),
                )
            ),
            id="profile requirements match requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: (
                profile["criteria"][-1]["requirementGroups"].pop(-1),
                profile["criteria"][-1]["requirementGroups"][0]["requirements"][0].update({"title": "test title"}),
                init_data.update({"_id": "a" * 32, "relatedCategory": category["id"], "criteria": profile["criteria"]}),
            ),
            lambda init_data, product, category: (
                product["requirementResponses"][0].update({"values": ["test_value"]}),
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "relatedProfiles" not in prod,
                    init_data.get("dateModified") == prod.get("dateModified"),
                )
            ),
            id="LOCALIZATION_CRITERIA criteria requirement groups do not match product's requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: (
                profile["criteria"][0]["requirementGroups"][0]["requirements"][0].update(
                    {"expectedValues": ["test_value"]}
                ),
                profile["criteria"][-1]["requirementGroups"][-1]["requirements"][0].update({"title": "test title"}),
                init_data.update({"_id": "a" * 32, "relatedCategory": category["id"], "criteria": profile["criteria"]}),
            ),
            lambda init_data, product, category: (
                product["requirementResponses"][0].update({"values": ["test_value"]}),
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "a" * 32 in prod["relatedProfiles"],
                    init_data.get("dateModified") != prod.get("dateModified"),
                )
            ),
            id="one of the LOCALIZATION_CRITERIA criteria requirement groups match product's requirementResponses",
        ),
        pytest.param(
            lambda init_data, profile, category: (
                profile["criteria"][0]["requirementGroups"][0]["requirements"][0].update(
                    {"expectedValues": ["test_value"]}
                ),
                init_data.update({"_id": "a" * 32, "relatedCategory": category["id"], "criteria": profile["criteria"]}),
            ),
            lambda init_data, product, category: (
                product["requirementResponses"][0].update({"values": ["test_value"]}),
                product["requirementResponses"].append(
                    {
                        "requirement": "Товар походить з однієї з країн, "
                        "що підписала Угоду про державні "
                        "закупівлі Світової Організації торгівлі "
                        "(GPA) або іншої країни з якою "
                        "Україна має міжнародні договори про державні закупівлі",
                        "value": "LT",
                        "classification": {
                            "scheme": "ESPD211",
                            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL",
                        },
                    }
                ),
                init_data.update(
                    {
                        "_id": "a" * 32,
                        "relatedCategory": category["id"],
                        "dateModified": "2026-01-01T00:00:00",
                        "requirementResponses": product["requirementResponses"],
                    }
                ),
            ),
            lambda init_data, prod: all(
                (
                    "relatedProfiles" not in prod,
                    init_data.get("dateModified") == prod.get("dateModified"),
                )
            ),
            id="multiple LOCALIZATION_CRITERIA criteria requirement groups match product's requirementResponses",
        ),
    ],
)
async def test_set_related_profiles(
    db, api, category, profile, product, setup_profile_data, setup_product_data, check_product
):
    test_profile = get_fixture_json("profile")
    setup_profile_data(test_profile, deepcopy(profile["data"]), category["data"])
    await db.profiles.insert_one(test_profile)

    test_product = get_fixture_json("product")
    setup_product_data(test_product, deepcopy(product["data"]), category["data"])
    await db.products.insert_one(test_product)

    await run_task()

    resp = await api.get(f'/api/products/{test_product["_id"]}')
    assert resp.status == 200
    resp_json = await resp.json()
    prod = resp_json["data"]
    assert check_product(test_product, prod)
