from catalog.serializers.base import ListSerializer, RootSerializer
from catalog.serializers.document import DocumentSerializer


class BanSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }
