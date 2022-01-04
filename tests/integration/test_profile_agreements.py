import random
from unittest.mock import patch, call

from catalog.migrations.cs_11945_profiles_agreement_id import migrate_profiles
from tests.integration.base import TEST_AUTH
from tests.integration.conftest import get_fixture_json


def create_agreements_side_effect(agreements):
    def load_agreements_by_classification(c_id, additional_classifications_ids):
        return [
            a for a in agreements
            if (
                a['classification']['id'] == c_id and
                {i['id'] for i in a.get("additionalClassifications", "")} == set(additional_classifications_ids)
            )
        ]
    return load_agreements_by_classification


@patch('catalog.migrations.cs_11945_profiles_agreement_id.logger')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profiles_one_scenario_ok(save_mock, load_agreements_mock, logger, api, category):
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
            'id': 'agreement_id_001',
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
            'procuringEntity': {'identifier': {'id': 'test.prozorro.ua'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    for p in profiles:
        request_data = get_fixture_json('profile')
        profile_id = f'{random.randint(0, 10**6):6d}-{category["data"]["id"]}'
        p['id'] = profile_id
        p['relatedCategory'] = category["data"]["id"]
        request_data.update(p)
        resp = await api.put(
            f"/api/profiles/{profile_id}",
            json={"data": request_data, "access": category["access"]},
            auth=TEST_AUTH,
        )

    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()

    assert logger.info.call_args_list == [
        call(f'found agreement_id for profile profile_id={p["id"]}, agreement_id=agreement_id_001, classification_id=33190000-8')
        for p in profiles
    ]
    save_mock.assert_called_once()
