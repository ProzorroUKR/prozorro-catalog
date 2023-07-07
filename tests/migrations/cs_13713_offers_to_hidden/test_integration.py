from uuid import uuid4
from copy import deepcopy

from catalog.migrations.cs_13713_offers_to_hidden import migrate
from tests.integration.conftest import db, api, get_fixture_json


async def test_migrate_offers(db, api):

    offer_fixture = get_fixture_json("offer")

    offers_id = []
    for i in range(1032):
        offer_data = deepcopy(offer_fixture)
        offer_data["_id"] = uuid4().hex
        offers_id.append(offer_data["_id"])
        if i % 100 == 0:
            offer_data["status"] = "hidden"
        await db.offers.insert_one(offer_data)

    counters = await migrate()
    assert counters.total_offers == 1032
    assert counters.updated_offers == 1021
    assert counters.skipped_offers == 11

    resp = await api.get(f'/api/offers/{offers_id[0]}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["status"] == "hidden"

    resp = await api.get(f'/api/offers/{offers_id[1]}')
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["data"]["status"] == "hidden"



