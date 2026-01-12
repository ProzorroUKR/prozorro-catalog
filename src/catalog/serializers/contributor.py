from catalog.serializers.ban import BanSerializer
from catalog.serializers.base import ListSerializer, RootSerializer
from catalog.serializers.document import DocumentSerializer


class ContributorSerializer(RootSerializer):
    serializers = {
        "bans": ListSerializer(BanSerializer),
        "documents": ListSerializer(DocumentSerializer),
    }
