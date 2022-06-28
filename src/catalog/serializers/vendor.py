from catalog.serializers.base import BaseSerializer, ListSerializer
from catalog.serializers.document import DocumentSignSerializer


class VendorSignSerializer(BaseSerializer):
    whitelist = {"categories", "vendor", "documents"}
    serializers = {
        "documents": ListSerializer(DocumentSignSerializer)
    }
