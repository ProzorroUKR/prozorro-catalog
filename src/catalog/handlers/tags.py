import logging
from typing import Optional, Union

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.models.api import ErrorResponse
from catalog.models.tag import TagList, TagResponse, TagCreateInput, TagUpdateInput
from catalog.auth import validate_accreditation
from catalog.serializers.base import BaseSerializer


logger = logging.getLogger(__name__)


class TagView(PydanticView):
    async def get(self, /, limit: Optional[int] = 100, active: Optional[bool] = None) -> r200[TagList]:
        """
        Get a list of tags

        Tags: Tags
        """
        response = await db.find_tags(limit=limit, active=active)
        return response

    async def post(
        self, /, body: TagCreateInput
    ) -> Union[r201[TagResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create tag

        Security: Basic: []
        Tags: Tags
        """
        validate_accreditation(self.request, "category")

        # export data back to dict
        data = body.data.dict_without_none()

        await db.insert_tag(data)

        logger.info(
            f"Created tag {data['id']}",
            extra={
                "MESSAGE_ID": "tag_create_post",
                "tag_id": data['id']
            },
        )
        return {"data": BaseSerializer(data).data}


class TagItemView(PydanticView):

    async def get(self, tag_id: str, /) -> Union[r200[TagResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get tag

        Tags: Tags
        """
        tag = await db.read_tag(tag_id)
        return {"data": BaseSerializer(tag).data}

    async def patch(
        self, tag_id: str, /, body: TagUpdateInput
    ) -> Union[r200[TagResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Tag update

        Security: Basic: []
        Tags: Tags
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_tag(tag_id) as tag:
            # export data back to dict
            data = body.data.dict_without_none()
            # update tag with valid data
            if tag["active"] is False and not data.get("active"):
                raise HTTPBadRequest(text="Forbidden to update inactive tag")

            tag.update(data)

            logger.info(
                f"Updated tag {tag_id}",
                extra={"MESSAGE_ID": "tag_patch"},
            )

        return {"data": BaseSerializer(tag).data}
