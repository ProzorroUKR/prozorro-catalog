from catalog.serializers.base import RootSerializer, ListSerializer
from catalog.serializers.document import DocumentSerializer
from catalog.serializers.product import ProductSerializer


class ProductRequestSerializer(RootSerializer):
    serializers = {
        "documents": ListSerializer(DocumentSerializer),
        "product": ProductSerializer,
    }
