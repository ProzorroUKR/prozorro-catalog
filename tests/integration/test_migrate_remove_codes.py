from migrations.cs_12110_remove_codes import migrate

from unittest.mock import patch, call


async def test_on_fixtures(db, profile, product):
    await db.profiles.update_many({}, {"$set": {"criteria.$[].code": "some_code"}})
    await db.products.update_many({}, {"$set": {"requirementResponses.$[].id": "some_id"}})
    old_profiles = await db.profiles.find({}).to_list(None)
    old_products = await db.products.find({}).to_list(None)
    with patch("migrations.cs_12110_remove_codes.logger") as logger:
        await migrate()
    stats = {'total_profiles': 1, 'updated_profiles': 1, 'total_products': 1, 'updated_products': 1}
    assert logger.info.call_args_list == [call("Start migration"), call(f"Finished. Stats: {stats}")]

    # test profiles
    updated_profiles = await db.profiles.find({}).to_list(None)
    assert len(updated_profiles) == 1
    assert updated_profiles[0]["_id"] == old_profiles[0]["_id"]
    assert len(updated_profiles[0]["criteria"]) == len(old_profiles[0]["criteria"])

    for before, after in zip(iter(old_profiles[0]["criteria"]), iter(updated_profiles[0]["criteria"])):
        assert "code" in before
        assert "code" not in after

    # test products
    updated_products = await db.products.find({}).to_list(None)
    assert len(updated_products) == 1
    assert updated_products[0]["_id"] == old_products[0]["_id"]
    assert len(updated_products[0]["requirementResponses"]) == len(old_products[0]["requirementResponses"])

    for before, after in zip(iter(old_products[0]["requirementResponses"]), iter(updated_products[0]["requirementResponses"])):
        assert "id" in before
        assert "id" not in after
