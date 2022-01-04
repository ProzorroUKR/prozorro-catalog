from unittest.mock import patch, Mock, MagicMock, call

from catalog.migrations.cs_11945_profiles_agreement_id import migrate_profiles



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
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_profiles')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profiles_one_scenario_ok(save_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            '_id': 'profile_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "access": {
                "owner": "test_owner"
            }
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert logger.info.call_args_list == [
        call('found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_001, classification_id=123456700-00'),
    ]


@patch('catalog.migrations.cs_11945_profiles_agreement_id.logger')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_profiles')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profile_iterate_over_classificactions(save_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            '_id': 'profile_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "access": {
                "owner": "test_owner"
            }
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_003',
            "classification": {
                "id": "123450000-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert logger.info.call_args_list == [
        call('found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_003, classification_id=123450000-00'),
    ]


@patch('catalog.migrations.cs_11945_profiles_agreement_id.logger')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_profiles')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profile_with_first_classification_only(save_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            '_id': 'profile_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "access": {
                "owner": "test_owner"
            }
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_002',
            "classification": {
                "id": "123456000-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_003',
            "classification": {
                "id": "123450000-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert logger.info.call_args_list == [
        call('found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_001, classification_id=123456700-00'),
    ]


@patch('catalog.migrations.cs_11945_profiles_agreement_id.logger')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_profiles')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profiles_additional_classification_not_matches(save_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            '_id': 'profile_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "access": {
                "owner": "test_owner"
            }
        },
    ]

    invalid_agreements = [
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "another_classification_id",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "another_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'some_other_agreement_type'
        },
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'some_other_owner'}},
            'agreementType': 'electronicCatalogue'
        },
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(invalid_agreements)
    await migrate_profiles()
    save_mock.assert_not_called()
    assert logger.info.call_args_list == [
        call('not found agreements for profile_id_001'),
    ]


@patch('catalog.migrations.cs_11945_profiles_agreement_id.logger')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_profiles')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification')
@patch('catalog.migrations.cs_11945_profiles_agreement_id.save')
async def test_migrate_profiles_several_agreements_for_one_profile(save_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            '_id': 'profile_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "access": {
                "owner": "test_owner"
            }
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_002',
            "classification": {
                "id": "123456700-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_not_called()
    assert logger.info.call_args_list == [
        call('too many agreements for profile_id_001'),
    ]

