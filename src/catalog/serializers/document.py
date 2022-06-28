from catalog.serializers.base import BaseSerializer
from catalog.context import get_request


def absolute_url_serializer(_, url):
    request = get_request()
    return f"{request.scheme}://{request.host}{url}"


class DocumentSerializer(BaseSerializer):
    serializers = {
        "url": absolute_url_serializer,
    }


class DocumentSignSerializer(BaseSerializer):
    whitelist = {"url", "hash", "title", "format"}
