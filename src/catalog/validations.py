import re

from aiohttp.web import HTTPBadRequest, HTTPForbidden

from catalog.models.category import CategoryStatus
from catalog.models.profile import ProfileStatus


def validate_product_related_category(category):
    if category['status'] != CategoryStatus.active:
        raise HTTPBadRequest(text="relatedCategory should be in `active` status.")


def validate_product_active_vendor(vendor):
    if not vendor['isActivated']:
        raise HTTPBadRequest(text="Vendor should be activated.")


# Validate product requirement responses
def validate_req_response_value(requirement, value, key):
    if value is None:
        raise HTTPBadRequest(text=f'requirement {key} should have value')
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


def validate_req_response_values(requirement, values, key):
    if not values:
        raise HTTPBadRequest(text=f'requirement {key} should have values')
    if not set(values).issubset(set(requirement['expectedValues'])):
        raise HTTPBadRequest(text=f'requirement {key} expectedValues')
    if 'expectedMinItems' in requirement and len(values) < requirement['expectedMinItems']:
        raise HTTPBadRequest(text=f'requirement {key} expectedMinItems')
    if 'expectedMaxItems' in requirement and len(values) > requirement['expectedMaxItems']:
        raise HTTPBadRequest(text=f'requirement {key} expectedMaxItems')


def validate_req_response(req_response, requirement):
    value = req_response.get('value')
    values = req_response.get('values')
    key = req_response.get('requirement')

    if any(i in requirement for i in ('expectedValue', 'minValue', 'maxValue', 'pattern')):
        validate_req_response_value(requirement, value, key)

    elif 'expectedValues' in requirement:
        validate_req_response_values(requirement, values, key)


def validate_product_req_responses_to_category(category: dict, product: dict, product_before=None):
    category_requirements = {
        r["title"]: r
        for c in category.get("criteria", "")
        for group in c["requirementGroups"]
        for r in group["requirements"]
    }

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
            and category_requirements[key].get("isArchived", False)
        ):
            raise HTTPBadRequest(text=f'requirement {key} is archived')

        requirement = category_requirements[key]
        validate_req_response(req_response, requirement)


def validate_product_req_response_to_profile(profile: dict, product: dict):
    requirements = {
        r["title"]: r
        for c in profile.get("criteria", "")
        for group in c["requirementGroups"]
        for r in group["requirements"]
    }

    if not requirements:
        raise HTTPBadRequest(text=f"product.relatedProfile({profile['id']}) should have at least one requirement")

    is_requirement_responded = False
    for req_response in product.get("requirementResponses", ""):
        key = req_response["requirement"]
        if key in requirements:
            is_requirement_responded = True
            requirement = requirements[key]
            validate_req_response(req_response, requirement)

    if not is_requirement_responded:
        raise HTTPBadRequest(text=f"should be responded at least on one profile({profile['id']}) requirement")


def validate_product_to_category(category, product, product_before=None):
    if product['classification']['id'][:4] != category['classification']['id'][:4]:
        raise HTTPBadRequest(text='product and category classification mismatch')

    validate_product_req_responses_to_category(category, product, product_before)


def validate_product_to_profile(profile, product):
    if product["relatedCategory"] != profile["relatedCategory"]:
        raise HTTPBadRequest(text='product and profile should be related with the same category')
    if profile["status"] != ProfileStatus.active:
        raise HTTPBadRequest(text="relatedProfiles should be in `active` status.")

    validate_product_req_response_to_profile(profile, product)


def validate_patch_vendor_product(product: dict) -> None:
    if product.get("vendor"):
        raise HTTPForbidden(text="Patch vendor product is disallowed")


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

        cat_data_type = requirements_statuses[key]["dataType"]
        if cat_data_type != req["dataType"]:
            raise HTTPBadRequest(text=f"requirement '{key}' dataType should be '{cat_data_type}' like in category")


def validate_requirement_title_uniq(profile: dict):
    req_titles = [
        req["title"]
        for criterion in profile.get("criteria", "")
        for rg in criterion.get("requirementGroups", "")
        for req in rg.get("requirements")
    ]
    if len(req_titles) != len(set(req_titles)):
        raise HTTPBadRequest(text="Requirement title should be unique")
