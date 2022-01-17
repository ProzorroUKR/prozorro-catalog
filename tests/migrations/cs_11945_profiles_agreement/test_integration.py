import random
from unittest.mock import patch

from catalog.migrations.cs_11945_profiles_agreement_id import migrate_profiles, Counters
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import (
    get_fixture_json,
    api,
    category
)


def create_agreements_side_effect(agreements):
    def load_agreements_by_classification(c_id, additional_classifications_ids):
        return [
            a for a in agreements
            if (
                a["classification"]["id"] == c_id and
                {i["id"] for i in a.get("additionalClassifications", "")} == set(additional_classifications_ids)
            )
        ]
    return load_agreements_by_classification


@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
async def test_migrate_profiles_one_scenario_ok(load_agreements_mock, api, category):
    profiles = [
        {
            "classification": {
                "description": "Медичне обладнання та вироби медичного призначення різні",
                "id": "33190000-8",
                "scheme": "ДК021"
            },
            "additionalClassifications": [
                {
                    "description": "Засоби індивідуального захисту (респіратори та маски) без клапану",
                    "id": "5011020",
                    "scheme": "KMU777"
                }
            ],
        },
    ]

    agreements = [
        {
            "id": "agreement_id_001",
            "classification": {
                "description": "Медичне обладнання та вироби медичного призначення різні",
                "id": "33190000-8",
                "scheme": "ДК021"
            },
            "additionalClassifications": [
                {
                    "description": "Засоби індивідуального захисту (респіратори та маски) без клапану",
                    "id": "5011020",
                    "scheme": "KMU777"
                }
            ],
            "procuringEntity": {"identifier": {"id": "test.prozorro.ua"}},
            "agreementType": "electronicCatalogue"
        }
    ]

    for p in profiles:
        request_data = get_fixture_json("profile")
        profile_id = f'{random.randint(10**5+1, 10**6):6d}-{category["data"]["id"]}'
        p["id"] = profile_id
        p["relatedCategory"] = category["data"]["id"]
        request_data.update(p)
        request_data.pop("agreementID")
        resp = await api.put(
            f"/api/profiles/{profile_id}",
            json={"data": request_data, "access": category["access"]},
            auth=TEST_AUTH,
        )

    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()

    for p in profiles:
        resp = await api.get(
            f"/api/profiles/{p['id']}",
            auth=TEST_AUTH,
        )
        data = await resp.json()
        assert data["data"]["agreementID"] == "agreement_id_001"


@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
async def test_migrate_500_profiles(load_agreements_mock, api, category):
    profile = {
        "classification": {
            "description": "Медичне обладнання та вироби медичного призначення різні",
            "id": "33190000-8",
            "scheme": "ДК021"
        },
        "additionalClassifications": [
            {
                "description": "Засоби індивідуального захисту (респіратори та маски) без клапану",
                "id": "5011020",
                "scheme": "KMU777"
            }
        ],
    }

    agreements = [
        {
            "id": "agreement_id_001",
            "classification": {
                "description": "Медичне обладнання та вироби медичного призначення різні",
                "id": "33190000-8",
                "scheme": "ДК021"
            },
            "additionalClassifications": [
                {
                    "description": "Засоби індивідуального захисту (респіратори та маски) без клапану",
                    "id": "5011020",
                    "scheme": "KMU777"
                }
            ],
            "procuringEntity": {"identifier": {"id": "test.prozorro.ua"}},
            "agreementType": "electronicCatalogue"
        }
    ]
    profiles = []

    for i in range(500):
        request_data = get_fixture_json("profile")
        request_data.update(profile)
        profile_id = f'{random.randint(10**5+1, 10**6):6d}-{category["data"]["id"]}'
        request_data["id"] = profile_id
        request_data["relatedCategory"] = category["data"]["id"]
        request_data.pop("agreementID")
        resp = await api.put(
            f"/api/profiles/{profile_id}",
            json={"data": request_data, "access": category["access"]},
            auth=TEST_AUTH,
        )

    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters == Counters(total_profiles=500, succeeded_profiles=500)

    for p in profiles:
        resp = await api.get(
            f'/api/profiles/{p["id"]}',
            auth=TEST_AUTH,
        )
        data = await resp.json()
        assert data["data"]["agreementID"] == "agreement_id_001"
