from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSignSerializer, DocumentSerializer


class VendorSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }


class VendorSignSerializer(RootSerializer):
    whitelist = {"categories", "vendor", "documents"}
    serializers = {
        "documents": ListSerializer(DocumentSignSerializer)
    }
