from catalog.serializers.base import RootSerializer


class ProductSerializer(RootSerializer):
    def __init__(self, data, vendor=None, show_owner=True):
        super().__init__(data, show_owner)
        if vendor and 'vendor' in data:
            data['vendor'].update({
                'name': vendor['vendor']['name'],
                'identifier': vendor['vendor']['identifier'],
            })
