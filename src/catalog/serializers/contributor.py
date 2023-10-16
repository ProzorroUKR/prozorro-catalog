from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer


class ContributorSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
    }
