from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from catalog.utils import get_now
from cron.activate_banned_vendors import run_task
from tests.integration.conftest import (
    get_fixture_json,
    api,
    db,
)


async def test_migrate_vendors(db, api):
    vendor_without_bans = get_fixture_json("vendor")
    vendor_without_bans["_id"] = uuid4().hex
    vendor_without_bans["status"] = "active"
    vendor_without_bans["dateModified"] = "2024-06-06T06:00:00+03:00"
    active_ban = get_fixture_json("ban")
    terminated_ban = deepcopy(active_ban)
    terminated_ban["dueDate"] = (get_now() - timedelta(minutes=1)).isoformat()

    await db.vendors.insert_one(vendor_without_bans)

    vendor_with_one_ban = deepcopy(vendor_without_bans)
    vendor_with_one_ban["_id"] = vendor_with_one_ban["vendor"]["identifier"]["id"] = uuid4().hex
    vendor_with_one_ban["status"] = "banned"
    vendor_with_one_ban["bans"] = [
        active_ban
    ]

    await db.vendors.insert_one(vendor_with_one_ban)

    vendor_with_two_ban = deepcopy(vendor_with_one_ban)
    vendor_with_two_ban["_id"] = vendor_with_two_ban["vendor"]["identifier"]["id"] = uuid4().hex
    vendor_with_two_ban["bans"] = [
        terminated_ban,
        active_ban
    ]

    await db.vendors.insert_one(vendor_with_two_ban)

    vendor_with_two_terminated_ban = deepcopy(vendor_with_one_ban)
    vendor_with_two_terminated_ban["_id"] = vendor_with_two_terminated_ban["vendor"]["identifier"]["id"] = uuid4().hex
    vendor_with_two_terminated_ban["bans"] = [
        terminated_ban,
        terminated_ban,
    ]

    await db.vendors.insert_one(vendor_with_two_terminated_ban)

    await run_task()

    vendor_data = await db.vendors.find_one({"_id": vendor_without_bans["_id"]})
    assert vendor_data["status"] == vendor_without_bans["status"]

    vendor_data_2 = await db.vendors.find_one({"_id": vendor_with_one_ban["_id"]})
    assert vendor_data_2["status"] == vendor_with_one_ban["status"]
    assert vendor_data_2["status"] == "banned"
    assert vendor_data_2["dateModified"] == vendor_with_one_ban["dateModified"]

    vendor_data_3 = await db.vendors.find_one({"_id": vendor_with_two_ban["_id"]})
    assert vendor_data_3["status"] == vendor_with_one_ban["status"]
    assert vendor_data_3["status"] == "banned"
    assert vendor_data_3["dateModified"] == vendor_with_two_ban["dateModified"]

    vendor_data_4 = await db.vendors.find_one({"_id": vendor_with_two_terminated_ban["_id"]})
    assert vendor_data_4["status"] != vendor_with_one_ban["status"]
    assert vendor_data_4["status"] == "active"
    assert vendor_data_4["dateModified"] != vendor_with_two_terminated_ban["dateModified"]
