from unittest.mock import patch, Mock, MagicMock

from catalog.migrations.profiles_agreement_id import migrate_profiles



def create_agreements_side_effect(agreements):
    def agreements_by_classifiaction_id(c_id):
        return [a for a in agreements if a['classification_id'] == c_id]
    return agreements_by_classifiaction_id


@patch('catalog.migrations.profiles_agreement_id.load_profiles')
@patch('catalog.migrations.profiles_agreement_id.load_agreements_by_id')
@patch('catalog.migrations.profiles_agreement_id.save')
async def test_migrate_profiles_one_scenario_ok(save_mock, load_agreements_mock, load_profiles_mock, capsys):
    profiles = [
        {
            'id': 'profile_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'owner': 'test_owner',
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert capsys.readouterr().out.split('\n')[:-1] == [
        'found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_001, classification_id=123456700-00',
    ]



@patch('catalog.migrations.profiles_agreement_id.load_profiles')
@patch('catalog.migrations.profiles_agreement_id.load_agreements_by_id')
@patch('catalog.migrations.profiles_agreement_id.save')
async def test_migrate_profile_iterate_over_classificactions(save_mock, load_agreements_mock, load_profiles_mock, capsys):
    profiles = [
        {
            'id': 'profile_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'owner': 'test_owner',
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_003',
            'classification_id': "123450000-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert capsys.readouterr().out.split('\n')[:-1] == [
        'found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_003, classification_id=123450000-00',
    ]


@patch('catalog.migrations.profiles_agreement_id.load_profiles')
@patch('catalog.migrations.profiles_agreement_id.load_agreements_by_id')
@patch('catalog.migrations.profiles_agreement_id.save')
async def test_migrate_profile_with_first_classification_only(save_mock, load_agreements_mock, load_profiles_mock, capsys):
    profiles = [
        {
            'id': 'profile_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'owner': 'test_owner',
        },
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_002',
            'classification_id': "123456000-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_003',
            'classification_id': "123450000-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_called_once()
    assert capsys.readouterr().out.split('\n')[:-1] == [
        'found agreement_id for profile profile_id=profile_id_001, agreement_id=agreement_id_001, classification_id=123456700-00',
    ]









@patch('catalog.migrations.profiles_agreement_id.load_profiles')
@patch('catalog.migrations.profiles_agreement_id.load_agreements_by_id')
@patch('catalog.migrations.profiles_agreement_id.save')
async def test_migrate_profiles_additional_classification_not_matches(save_mock, load_agreements_mock, load_profiles_mock, capsys):
    profiles = [
        {
            'id': 'profile_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'owner': 'test_owner',
        },
    ]

    invalid_agreements = [
        {
            'id': 'agreement_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "additionalClassifications_id_invalid"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_002',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "invaild_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_003',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'some_other_agreement_type'
        },
        {
            'id': 'agreement_id_004',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'some_another_owner'}},
            'agreementType': 'electronicCatalogue'
        },
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(invalid_agreements)
    await migrate_profiles()
    save_mock.assert_not_called()
    assert capsys.readouterr().out.split('\n')[:-1] == [
        'not found agreements for profile_id_001',
    ]


@patch('catalog.migrations.profiles_agreement_id.load_profiles')
@patch('catalog.migrations.profiles_agreement_id.load_agreements_by_id')
@patch('catalog.migrations.profiles_agreement_id.save')
async def test_migrate_profiles_several_agreements_for_one_profile(save_mock, load_agreements_mock, load_profiles_mock, capsys):
    profiles = [
        {
            'id': 'profile_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'owner': 'test_owner',
        }
    ]

    agreements = [
        {
            'id': 'agreement_id_001',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        },
        {
            'id': 'agreement_id_002',
            'classification_id': "123456700-00",
            'additionalClassifications': [{"id": "test_additionalClassifications_id_001"}],
            'scheme': "test_scheme",
            'procuringEntity': {'identifier': {'id': 'test_owner'}},
            'agreementType': 'electronicCatalogue'
        }
    ]

    load_profiles_mock.return_value = profiles
    load_agreements_mock.side_effect = create_agreements_side_effect(agreements)
    await migrate_profiles()
    save_mock.assert_not_called()
    assert capsys.readouterr().out.split('\n')[:-1] == [
        'too many agreements for profile_id_001',
    ]

