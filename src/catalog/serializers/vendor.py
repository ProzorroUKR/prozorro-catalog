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

    @property
    def data(self) -> dict:
        data = super().data
        for ban in data.get("bans", []):
            if datetime.fromisoformat(ban["dueDate"]) > get_now():
                data["isBanned"] = True
                break
        else:
            data["isBanned"] = False
        return data


class VendorSignSerializer(RootSerializer):
    whitelist = {"categories", "vendor", "documents"}
    serializers = {
        "documents": ListSerializer(DocumentSignSerializer)
    }
