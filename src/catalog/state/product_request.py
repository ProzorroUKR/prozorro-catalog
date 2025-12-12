from catalog.state.base import BaseState
from catalog.state.product import ProductState
from catalog.context import get_now, get_request
from uuid import uuid4

from catalog.utils import convert_requests_documents_url


class ProductRequestState(BaseState):

    @classmethod
    async def on_post(cls, data, category):
        data["dateCreated"] = get_now().isoformat()
        data["owner"] = get_request().user.name
        for doc in data.get("documents", []):
            doc["datePublished"] = doc["dateModified"] = get_now().isoformat()
        for doc in data.get("documents", []):
            convert_requests_documents_url(doc, data["id"])

        super().on_post(data)

    @classmethod
    def always(cls, data):
        data["dateModified"] = get_now().isoformat()

    @classmethod
    async def on_accept(cls, data, category, acceptation_date):
        data["product"]["id"] = uuid4().hex
        data["product"]["dateModified"] = data["product"]["dateCreated"] = data["dateModified"] = acceptation_date
        data["product"]["owner"] = get_request().user.name
        ProductState.copy_data_from_category(data["product"], category)
