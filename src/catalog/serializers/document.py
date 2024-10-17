from catalog.serializers.base import BaseSerializer
from catalog.context import get_request, get_request_scheme


def absolute_url_serializer(_, url, **kwargs):
    request = get_request()
    req_scheme = get_request_scheme()
    return f"{req_scheme}://{request.host}{url}"


class DocumentSerializer(BaseSerializer):
    serializers = {
        "url": absolute_url_serializer,
    }


class DocumentSignSerializer(BaseSerializer):
    whitelist = {"url", "hash", "title", "format"}
