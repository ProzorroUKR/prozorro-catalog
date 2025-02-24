import re
from datetime import datetime
from typing import Iterable

import aiohttp
from aiohttp.web import HTTPBadRequest, HTTPForbidden
from aiohttp_client_cache import CachedSession

from catalog.models.category import CategoryStatus
from catalog.models.profile import ProfileStatus
from catalog.models.criteria import TYPEMAP
from catalog.settings import (
    CACHE_BACKEND,
    LOCALIZATION_CRITERIA,
    MEDICINE_API_URL,
    MEDICINE_SCHEMES,
    OPENPROCUREMENT_API_URL,
)
from catalog.utils import get_now


def validate_product_related_category(category):
    if category['status'] != CategoryStatus.active:
        raise HTTPBadRequest(text="relatedCategory should be in `active` status")
    localization_criteria = [
        cr for cr in category['criteria'] if cr.get("classification", {}).get("id") == LOCALIZATION_CRITERIA
    ]
    if not localization_criteria:
        raise HTTPBadRequest(text="relatedCategory must have localization criteria")


def validate_active_vendor(vendor):
    if not vendor['isActivated']:
        raise HTTPBadRequest(text="Vendor should be activated.")
    for ban in vendor.get("bans", []):
        if datetime.fromisoformat(ban["dueDate"]) > get_now():
            raise HTTPForbidden(text="Vendor is banned")


def validate_req_response_values(requirement, values, key):
    if not values:
        raise HTTPBadRequest(text=f'requirement {key} should have values')
    data_type = requirement.get("dataType")
    data_type = TYPEMAP.get(data_type)

    for value in values:
        if not data_type or not isinstance(value, data_type):
            raise HTTPBadRequest(text=f'requirement {key} value has unexpected type')
        if requirement.get("dataType") == "number" and isinstance(value, bool):
            raise HTTPBadRequest(text=f'requirement {key} value has unexpected type')

        if (
            'expectedValue' in requirement
            and value != requirement['expectedValue']
        ):
            raise HTTPBadRequest(text=f'requirement {key} unexpected value')
        if 'minValue' in requirement and value < requirement['minValue']:
            raise HTTPBadRequest(text=f'requirement {key} minValue')
        if 'maxValue' in requirement and value > requirement['maxValue']:
            raise HTTPBadRequest(text=f'requirement {key} maxValue')
        if 'pattern' in requirement and not re.match(
                requirement['pattern'], str(value)
        ):
            raise HTTPBadRequest(text=f'requirement {key} pattern')
    if 'expectedValues' in requirement and not set(values).issubset(set(requirement['expectedValues'])):
        raise HTTPBadRequest(text=f'requirement {key} expectedValues')
    if 'expectedMinItems' in requirement and len(values) < requirement['expectedMinItems']:
        raise HTTPBadRequest(text=f'requirement {key} expectedMinItems')
    if 'expectedMaxItems' in requirement and len(values) > requirement['expectedMaxItems']:
        raise HTTPBadRequest(text=f'requirement {key} expectedMaxItems')


def validate_req_response(req_response, requirement):
    value = req_response.get('value')
    values = req_response.get('values')
    if requirement.get("expectedValues") is not None and value is not None:
        raise HTTPBadRequest(text=f"only 'values' allowed in response for requirement {requirement['title']}")
    elif requirement.get("expectedValues") is None and values is not None:
        raise HTTPBadRequest(text=f"only 'value' allowed in response for requirement {requirement['title']}")
    values = [value] if value is not None else values
    key = req_response.get('requirement')

    validate_req_response_values(requirement, values, key)


def validate_product_req_responses_to_category(
        category: dict,
        product: dict,
        product_before: dict = None,
        required_criteria: Iterable = None
):

    category_requirements = {
        r["title"]: (r, c.get("classification", {}).get("id"))
        for c in category.get("criteria", "")
        for group in c["requirementGroups"]
        for r in group["requirements"]
    }
    category_criteria = [
        c.get("classification", {}).get("id")
        for c in category.get("criteria", "")
    ]
    required_criteria = required_criteria if required_criteria else category_criteria
    required_classifications = {i[1] for i in category_requirements.values() if i[1] in required_criteria}
    responded_classifications = set()

    if category_requirements and not product.get("requirementResponses"):
        raise HTTPBadRequest(text='should be responded at least on one category requirement')

    before_responded_requirements = {}
    if product_before:
        before_responded_requirements = {r["requirement"] for r in product_before.get("requirementResponses", "")}

    for req_response in product.get("requirementResponses", ""):
        key = req_response['requirement']

        if key not in category_requirements:
            raise HTTPBadRequest(text=f'requirement {key} not found')

        # check if added new requirement responses to archived requirement
        if (
            key not in before_responded_requirements
            and category_requirements[key][0].get("isArchived", False)
        ):
            raise HTTPBadRequest(text=f'requirement {key} is archived')

        requirement, classification = category_requirements[key]
        validate_req_response(req_response, requirement)
        responded_classifications.add(classification)

    for required_classification in required_classifications:
        if required_classification not in responded_classifications:
            raise HTTPBadRequest(text=f'should be responded at least on one category '
                                      f'requirement with classification {required_classification}')


def validate_product_req_response_to_profile(profile: dict, product: dict):
    for criterion in profile.get("criteria", ""):
        requirements = {
            r["title"]: r
            for group in criterion["requirementGroups"]
            for r in group["requirements"]
        }
        if not requirements:
            raise HTTPBadRequest(text=f"product.relatedProfile({profile['id']}) should have at least one requirement for criteria {criterion['title']}")

        is_requirement_responded = False
        for req_response in product.get("requirementResponses", ""):
            key = req_response["requirement"]
            if key in requirements:
                is_requirement_responded = True
                requirement = requirements[key]
                validate_req_response(req_response, requirement)

        if not is_requirement_responded:
            raise HTTPBadRequest(text=f"should be responded at least on one profile({profile['id']}) requirement for criteria {criterion['title']}")


def validate_product_to_category(
        category,
        product,
        product_before=None,
        check_classification=True,
        required_criteria=None
):
    if category.get("status", CategoryStatus.active) != CategoryStatus.active:
        raise HTTPBadRequest(text=f"relatedCategory should be in `{CategoryStatus.active}` status.")
    if check_classification:
        category_class = category["classification"]["id"]
        if (category_class[:3] == "336" and product["classification"]["id"][:3] != category_class[:3]) or \
                (category_class[:3] != "336" and product["classification"]["id"][:4] != category_class[:4]):
            raise HTTPBadRequest(
                text="product classification should have the same digits at the beginning as in related category."
            )

    validate_product_req_responses_to_category(category, product, product_before, required_criteria)


def validate_product_to_profile(profile, product):
    if product["relatedCategory"] != profile["relatedCategory"]:
        raise HTTPBadRequest(text='product and profile should be related with the same category')
    if profile["status"] == ProfileStatus.hidden:
        raise HTTPBadRequest(text=f"relatedProfiles should be in `{ProfileStatus.active}` status")

    validate_product_req_response_to_profile(profile, product)


def validate_profile_requirements(new_requirements: list, category: dict) -> None:
    requirements_statuses = {
        r["title"]: r
        for c in category.get("criteria", "")
        for rg in c.get("requirementGroups", "")
        for r in rg.get("requirements")
    }

    for req in new_requirements:
        key = req["title"]
        if key not in requirements_statuses:
            raise HTTPBadRequest(text=f"requirement '{key}' not found in category {category['id']}")

        if requirements_statuses[key].get("isArchived", False):
            raise HTTPBadRequest(text=f"requirement '{key}' is archived")

        cat_data_type = requirements_statuses[key].get("dataType")
        if cat_data_type != req.get("dataType"):
            raise HTTPBadRequest(text=f"requirement '{key}' dataType should be '{cat_data_type}' like in category")
        if (
            req.get("dataType") == "boolean"
            and any(req.get(field_name) is not None for field_name in ("minValue", "maxValue", "expectedValues"))
        ):
            raise HTTPBadRequest(text=f"requirement '{key}': for boolean use only expectedValue")
        if (
            "expectedValue" in requirements_statuses[key]
            and req.get("expectedValue") != requirements_statuses[key]["expectedValue"]
        ):
            raise HTTPBadRequest(text=f"requirement '{key}' expectedValue should be like in category")
        if expected_values := requirements_statuses[key].get("expectedValues"):
            if not req.get("expectedValues") or set(req["expectedValues"]).difference(set(expected_values)):
                raise HTTPBadRequest(
                    text=f"requirement '{key}' expectedValues should have values from category requirement"
                )
            validate_requirement_values_range(req, requirements_statuses, key, "expectedMinItems", "expectedMaxItems")
        validate_requirement_values_range(req, requirements_statuses, key, "minValue", "maxValue")


def validate_requirement_values_range(requirement, parent_requirement, key, min_value_field, max_value_field):
    # TODO: remove after migration data type check
    if (
        parent_requirement[key].get(min_value_field) is not None
        and (
            requirement.get(min_value_field) is not None
            and isinstance(requirement[min_value_field], (float, int))
            and isinstance(parent_requirement[key][min_value_field], (float, int))
            and requirement[min_value_field] < parent_requirement[key][min_value_field]
        )
    ):
        raise HTTPBadRequest(text=f"requirement '{key}' {min_value_field} should be equal or greater than in category")
    if (
        parent_requirement[key].get(max_value_field) is not None
        and
        (
            requirement.get(max_value_field) is None
            or (
                isinstance(requirement[max_value_field], (float, int))
                and isinstance(parent_requirement[key][max_value_field], (float, int))
                and requirement[max_value_field] > parent_requirement[key][max_value_field]
            )
        )
    ):
        raise HTTPBadRequest(text=f"requirement '{key}' {max_value_field} should be equal or less than in category")


def validate_requirement_title_uniq(profile: dict):
    req_titles = [
        req["title"]
        for criterion in profile.get("criteria", "")
        for rg in criterion.get("requirementGroups", "")
        for req in rg.get("requirements")
    ]
    if len(req_titles) != len(set(req_titles)):
        raise HTTPBadRequest(text="Requirement title should be unique")


def validate_criteria_classification_uniq(obj: dict, updated_criterion=None):
    criteria = obj.get("criteria", [])
    if updated_criterion:
        if classification_id := updated_criterion.get("classification", {}).get("id"):
            criterion_id = updated_criterion["id"]
            if any(
                criterion["classification"]["id"] == classification_id and criterion["id"] != criterion_id
                for criterion in criteria
            ):
                raise HTTPBadRequest(text="Criteria with this classification already exists")
    else:
        classification_ids = [criterion["classification"]["id"] for criterion in criteria if criterion.get("classification")]
        if len(classification_ids) != len(set(classification_ids)):
            raise HTTPBadRequest(text="Criteria classification should be unique")


def validate_criteria_max_items_on_post(obj: dict, obj_title: str):
    if len(obj.get(obj_title, "")) > 1:
        raise HTTPBadRequest(text=f"Size of {obj_title} cannot be greater then 1")


def validate_contributor_banned_categories(category: dict, contributor: dict):
    category_administrator = category.get("marketAdministrator", {}).get("identifier", {}).get("id")
    for ban in contributor.get("bans", []):
        ban_administrator = ban.get("administrator", {}).get("identifier", {}).get("id")
        if ban_administrator == category_administrator\
                and ("dueDate" not in ban or datetime.fromisoformat(ban["dueDate"]) > get_now()):
            raise HTTPBadRequest(text="request for product with this relatedCategory is forbidden due to ban")


def validate_previous_product_reviews(product_request: dict):
    if product_request.get("acception") or product_request.get("rejection"):
        raise HTTPBadRequest(text="product request is already reviewed")


def validate_contributor_ban_already_exists(contributor: dict, administrator_id):
    for ban in contributor.get("bans", []):
        if ban.get("administrator", {}).get("identifier", {}).get("id") == administrator_id \
                and ("dueDate" not in ban or datetime.fromisoformat(ban["dueDate"]) > get_now()):
            raise HTTPBadRequest(text="ban from this market administrator already exists")


def validate_category_administrator(administrator_data: dict, category: dict):
    if administrator_data.get("administrator", {}).get("identifier", {}).get("id") != \
            category.get("marketAdministrator", {}).get("identifier", {}).get("id"):
        raise HTTPBadRequest(text="only administrator who is related to product category can moderate product request.")


async def validate_medicine_additional_classifications(obj: dict):
    med_values = {scheme: [] for scheme in MEDICINE_SCHEMES}
    for classification in obj.get("additionalClassifications", []):
        if classification["scheme"] in MEDICINE_SCHEMES:
            med_values[classification["scheme"]].append(classification["id"])
    for scheme, ids in med_values.items():
        if ids:
            async with CachedSession(cache=CACHE_BACKEND) as session:
                async with session.get(f'{MEDICINE_API_URL}/registry/{scheme.lower()}.json') as resp:
                    if resp.status != 200:
                        raise HTTPBadRequest(text=f"Can't get classification {scheme} from medicine "
                                                  f"registry, please make request later")
                    response = await resp.json()
                    data = response["data"]
                    if diff_values := set(ids).difference(data.keys()):
                        raise HTTPBadRequest(
                            text=f"values {diff_values} don't exist in {scheme} dictionary"
                        )


async def validate_agreement(category):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{OPENPROCUREMENT_API_URL}/agreements/{category["agreementID"]}') as resp:
            if resp.status == 404:
                raise HTTPBadRequest(text="Agreement doesn't exist")
            if resp.status != 200:
                raise HTTPBadRequest(text="Can't get agreement from openprocurement api, "
                                          "plz make request later")
            data = await resp.json()
            agreement = data["data"]
            if agreement.get("status", "") != "active":
                raise HTTPBadRequest(text="Agreement not in `active` status")
            agr_clas_id = agreement["classification"]["id"]
            cat_clas_id = category["classification"]["id"]
            if agr_clas_id[0:3] != cat_clas_id[0:3]:
                raise HTTPBadRequest(text="Agreement:classification:id first three numbers "
                                          "should be equal to Category:classification:id")
