from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSignSerializer, DocumentSerializer


def calculate_vendor_status(vendor):
    status = "active" if vendor.get("isActive") else "pending"
    return status


class VendorSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }
    calculated = {
        "status": calculate_vendor_status,
    }


class VendorSignSerializer(RootSerializer):
    whitelist = {"categories", "vendor", "documents"}
    serializers = {
        "documents": ListSerializer(DocumentSignSerializer)
    }
