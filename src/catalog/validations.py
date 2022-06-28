from aiohttp.web import HTTPBadRequest

from catalog.models.profile import ProfileStatus


def validate_related_profile(profile):
    if profile['status'] != ProfileStatus.active:
        raise HTTPBadRequest(text="relatedProfile should be in `active` status.")


def validate_active_vendor(vendor):
    if not vendor['isActive']:
        raise HTTPBadRequest(text="Vendor should be activated.")
