from aiohttp.web import HTTPBadRequest

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
