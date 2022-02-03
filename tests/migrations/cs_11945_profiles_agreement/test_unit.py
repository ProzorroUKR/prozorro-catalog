from unittest.mock import patch, call

from catalog.migrations.cs_11945_profiles_agreement_id import migrate_profiles


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


async def aiter(iterable):
    for i in iterable:
        yield i


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_one_scenario_ok(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType": "electronicCatalogue",
            "status": "active",
        },
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    update_mock.assert_called_once()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 1
    required_log = "Resolved profile_id_001. Found agreement_id for profile agreement_id=agreement_id_001, classification_id=123456700-00"
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profile_iterate_over_classifications(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_003",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType": "electronicCatalogue",
            "status": "active",
        }
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    update_mock.assert_called_once()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 1
    required_log = "Resolved profile_id_001. Found agreement_id for profile agreement_id=agreement_id_003, classification_id=123450000-00"
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profile_with_first_classification_only(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_002",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType": "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_003",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        }
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 1
    update_mock.assert_called_once()
    required_log = "Resolved profile_id_001. Found agreement_id for profile agreement_id=agreement_id_001, classification_id=123456700-00"
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_additional_classification_not_matches(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType": "some_other_agreement_type"
        },
        {
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "some_other_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(invalid_agreements)
    counters = await migrate_profiles()
    update_mock.assert_not_called()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 0
    assert counters.no_agreement_profiles == 1
    required_log = "Failed profile_id_001. Not found agreements for profile_id_001."
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_several_agreements_for_one_profile(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_002",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 0
    assert counters.too_many_agreement_profiles == 1
    update_mock.assert_not_called()
    required_log = "Failed profile_id_001. Too many agreements for profile_id_001 at 123456700-00."
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_only_active_agreement(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_002",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "deactivated",
        },
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 1
    assert counters.too_many_agreement_profiles == 0
    update_mock.assert_called_once()
    required_log = "Resolved profile_id_001. Found agreement_id for profile agreement_id=agreement_id_001, classification_id=123456700-00"
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_only_active_agreement(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            "id": "agreement_id_001",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "active",
        },
        {
            "id": "agreement_id_002",
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
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType":  "electronicCatalogue",
            "status": "deactivated",
        },
    ]

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters.total_profiles == 1
    assert counters.succeeded_profiles == 1
    assert counters.too_many_agreement_profiles == 0
    update_mock.assert_called_once()
    required_log = "Resolved profile_id_001. Found agreement_id for profile agreement_id=agreement_id_001, classification_id=123456700-00"
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_skip_if_provided(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
            },
            "agreementID": "agreementID"
        },
    ]

    agreements = []
    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    counters = await migrate_profiles()
    assert counters.total_profiles == 1
    assert counters.skipped_profiles == 1
    update_mock.assert_not_called()
    required_log = "Skipped profile_id_001. agreementID already exists."
    assert call(required_log) in logger.debug.call_args_list


@patch("catalog.migrations.cs_11945_profiles_agreement_id.logger")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_profiles")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.load_agreements_by_classification")
@patch("catalog.migrations.cs_11945_profiles_agreement_id.update_profile")
async def test_migrate_profiles_continues_after_rised_exception(update_mock, load_agreements_mock, load_profiles_mock, logger):
    profiles = [
        {
            "_id": "profile_id_001",
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
        {
            "_id": "profile_id_002",
            "classification": {
                "id": "129999900-00",
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
            "id": "agreement_id_001",
            "classification": {
                "id": "129999900-00",
                "scheme": "test_main_scheme"
            },
            "additionalClassifications": [
                {
                    "id": "111111",
                    "scheme": "test_additional_scheme"
                }
            ],
            "procuringEntity": {"identifier": {"id": "test_owner"}},
            "agreementType": "electronicCatalogue",
            "status": "active",
        },
    ]

    f = create_agreements_side_effect(agreements)
    def load_arguments_raises_error(c_id, additional_classifications_ids):
        if c_id == "123456700-00":
            raise ValueError
        return f(c_id, additional_classifications_ids)

    load_profiles_mock.return_value = aiter(profiles)
    load_agreements_mock.side_effect = load_arguments_raises_error
    counters = await migrate_profiles()
    assert counters.total_profiles == 2
    assert counters.skipped_profiles == 1
    assert counters.succeeded_profiles == 1
    required_log = "Failed profile_id_001. Caught ValueError."
    assert call(required_log) in logger.debug.call_args_list
    required_log = ("Resolved profile_id_002. Found agreement_id for profile agreement_id=agreement_id_001, "
                    "classification_id=129999900-00")
    assert call(required_log) in logger.debug.call_args_list
