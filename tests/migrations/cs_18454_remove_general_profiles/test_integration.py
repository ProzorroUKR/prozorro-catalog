from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from catalog.migrations.cs_18454_remove_general_profiles import migrate
from catalog.utils import get_now
from tests.integration.conftest import api, category, db, get_fixture_json, mock_agreement


async def test_migrate_profiles(db, api, category, mock_agreement):
    general_profile = deepcopy(get_fixture_json("profile"))
    general_profile["_id"] = uuid4().hex
    general_profile["status"] = "general"
    general_profile["dateModified"] = (get_now() - timedelta(days=1)).isoformat()
    await db.profiles.insert_one(general_profile)

    active_profile = deepcopy(get_fixture_json("profile"))
    active_profile["_id"] = uuid4().hex
    active_profile["dateModified"] = (get_now() - timedelta(days=2)).isoformat()
    await db.profiles.insert_one(active_profile)

    await migrate()
    profile_1_new = await db.profiles.find_one({"_id": general_profile["_id"]})
    assert profile_1_new["status"] == "hidden"
    assert profile_1_new["dateModified"] > general_profile["dateModified"]

    profile_2_new = await db.profiles.find_one({"_id": active_profile["_id"]})
    assert profile_2_new["status"] == active_profile["status"]
    assert profile_2_new["dateModified"] == active_profile["dateModified"]
