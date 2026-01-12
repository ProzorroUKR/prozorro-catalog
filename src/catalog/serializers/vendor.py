from catalog.serializers.ban import BanSerializer
from catalog.serializers.base import ListSerializer, RootSerializer
from catalog.serializers.document import DocumentSerializer, DocumentSignSerializer


class VendorSerializer(RootSerializer):
    serializers = {
        "bans": ListSerializer(BanSerializer),
        "documents": ListSerializer(DocumentSerializer),
    }


class VendorSignSerializer(RootSerializer):
    whitelist = {"vendor", "documents"}
    serializers = {"documents": ListSerializer(DocumentSignSerializer)}
