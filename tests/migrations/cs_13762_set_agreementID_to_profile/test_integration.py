from copy import deepcopy

from catalog.migrations.cs_13762_set_agreementID_to_profile import migrate
from tests.integration.conftest import db, api, category, mock_agreement, get_fixture_json


async def test_migrate_profiles(db, api, mock_agreement, category):

    category = category["data"]
    profile_fixture = get_fixture_json("profile")

    for i in range(1, 4):
        profile_data = deepcopy(profile_fixture)
        profile_data["_id"] = f"{i}" * 32
        profile_data["relatedCategory"] = category["id"]
        await db.profiles.insert_one(profile_data)

    counters = await migrate()
    assert counters.total_categories == 1
    assert counters.total_profiles == 3
    assert counters.updated_profiles == 3
    assert counters.skipped_profiles == 0
