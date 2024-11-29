from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer


class BanSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }
