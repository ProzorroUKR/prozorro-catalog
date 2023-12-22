from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from catalog.migrations.cs_15522_profiles_date_created import migrate
from catalog.utils import get_now
from tests.integration.conftest import api, category, db, get_fixture_json, mock_agreement


async def test_migrate_profiles(db, api, category, mock_agreement):
    profile = deepcopy(get_fixture_json("profile"))
    profile["_id"] = uuid4().hex
    profile["relatedCategory"] = category["data"]["id"]
    profile["dateModified"] = (get_now() - timedelta(days=1)).isoformat()
    await db.profiles.insert_one(profile)

    profile_2 = deepcopy(profile)
    profile_2["_id"] = uuid4().hex
    profile_2["dateModified"] = (get_now() - timedelta(days=2)).isoformat()
    await db.profiles.insert_one(profile_2)

    profile_3 = deepcopy(profile)
    profile_3["_id"] = uuid4().hex
    profile_3["dateModified"] = (get_now() - timedelta(days=2)).isoformat()
    date_created = (get_now() - timedelta(days=5)).isoformat()
    profile_3["dateCreated"] = date_created
    await db.profiles.insert_one(profile_3)

    await migrate()
    profile_1_new = await db.profiles.find_one({"_id": profile["_id"]})
    assert profile_1_new["dateCreated"] == profile["dateModified"]
    assert profile_1_new["dateModified"] > profile["dateModified"]

    profile_2_new = await db.profiles.find_one({"_id": profile_2["_id"]})
    assert profile_2_new["dateCreated"] == profile_2["dateModified"]
    assert profile_2_new["dateModified"] > profile_2["dateModified"]

    profile_3_new = await db.profiles.find_one({"_id": profile_3["_id"]})
    assert profile_3_new["dateCreated"] != profile_3["dateModified"]
    assert profile_3_new["dateCreated"] == date_created
    assert profile_3_new["dateModified"] == profile_3["dateModified"]
