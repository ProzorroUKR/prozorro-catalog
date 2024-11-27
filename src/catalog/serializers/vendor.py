from datetime import datetime

from catalog.context import get_now
from catalog.serializers.ban import BanSerializer
from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSignSerializer, DocumentSerializer


class VendorSerializer(RootSerializer):
    serializers = {
        "bans": ListSerializer(BanSerializer),
        "documents": ListSerializer(DocumentSerializer),
    }


class VendorSignSerializer(RootSerializer):
    whitelist = {"categories", "vendor", "documents"}
    serializers = {
        "documents": ListSerializer(DocumentSignSerializer)
    }
