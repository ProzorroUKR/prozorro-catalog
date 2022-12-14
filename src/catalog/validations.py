from aiohttp.web import HTTPBadRequest, HTTPForbidden

from catalog.models.profile import ProfileStatus, Profile


def validate_product_related_profile(profile):
    if profile['status'] != ProfileStatus.active:
        raise HTTPBadRequest(text="relatedProfile should be in `active` status.")


def validate_product_active_vendor(vendor):
    if not vendor['isActivated']:
        raise HTTPBadRequest(text="Vendor should be activated.")


def validate_product_to_profile(profile, product):
    if product['classification']['id'][:4] != profile['classification']['id'][:4]:
        raise HTTPBadRequest(text='product and profile classification mismatch')

    try:
        Profile.validate_product(profile, product)
    except ValueError as e:
        raise HTTPBadRequest(text=e.args[0])


def validate_patch_vendor_product(product: dict) -> None:
    if product.get("vendor"):
        raise HTTPForbidden(text="Patch vendor product is disallowed")


def validate_requirement_title_uniq(profile: dict):
    req_titles = [
        req["title"]
        for criterion in profile.get("criteria", "")
        for rg in criterion.get("requirementGroups", "")
        for req in rg.get("requirements")
    ]
    if len(req_titles) != len(set(req_titles)):
        raise HTTPForbidden(text="Requirement title should be unique")
