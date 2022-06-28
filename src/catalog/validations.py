from aiohttp.web import HTTPBadRequest

from catalog.models.profile import ProfileStatus


def validate_related_profile(profile):
    if profile['status'] != ProfileStatus.active:
        raise HTTPBadRequest(text="relatedProfile should be in `active` status")
