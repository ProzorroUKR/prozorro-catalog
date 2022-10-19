import pytest

from migrations.cs_12300_replace_anyof_with_expected_values import migrate_profile
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    api,
    profile,
    product
)


@pytest.mark.skip(reason="this currently doesn't work correctly")
async def test_migrate_profiles(db, profile, product):
    criteria = profile["data"]["criteria"]
    for c in criteria:
        for rg in c["requirementGroups"]:
            requirement = rg["requirements"][0]
            if "expectedValues" in requirement:
                requirement["anyOf"] = requirement["expectedValues"][:]
                del requirement["expectedValues"]
                if "expectedMaxItems" in requirement:
                    del requirement["expectedMaxItems"]
                if "expectedMinItems" in requirement:
                    del requirement["expectedMinItems"]
    await db.profiles.update_many({}, {"$set": {"criteria": criteria}})

    for resp in product["data"]['requirementResponses']:
        if "values" in resp:
            resp["value"] = resp["values"][0]
            del resp["values"]
    await db.products.update_many({}, {"$set": {"requirementResponses": product["data"]['requirementResponses']}})

    counters = await migrate_profile(profile["data"]["id"])

    assert counters["profiles"] == 1
    assert counters["products"] == 1
    assert counters["skipped_profiles"] == 0
    assert counters["total_profiles"] == 1
    assert counters["requirements"] == 3
    assert counters["responses"] == 3

    counters = await migrate_profile(profile["data"]["id"])
    assert counters["profiles"] == 0
    assert counters["products"] == 0
    assert counters["skipped_profiles"] == 1
    assert counters["total_profiles"] == 1
    assert counters["requirements"] == 0
    assert counters["responses"] == 0
