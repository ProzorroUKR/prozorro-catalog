from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest
from catalog.swagger import class_view_swagger_path
from catalog.settings import IMG_PATH, IMG_DIR, IMG_STORE_DIR_NAME_LEN, IMG_STORE_DIR_LEVELS, ALLOWED_IMG_TYPES
from uuid import uuid4
from os import makedirs
import aiofiles
import aiofiles.os
import imghdr
import hashlib
import logging
import os.path


async_make_dirs = aiofiles.os.wrap(makedirs)


async def generate_filename():
    full_path = IMG_DIR
    filename = uuid4().hex

    if IMG_STORE_DIR_LEVELS:
        sub_path = [filename[i:i+IMG_STORE_DIR_NAME_LEN]
                    for i in range(0, IMG_STORE_DIR_LEVELS * IMG_STORE_DIR_NAME_LEN, IMG_STORE_DIR_NAME_LEN)]
        filename = filename[IMG_STORE_DIR_LEVELS * IMG_STORE_DIR_NAME_LEN:]

        full_path = os.path.join(IMG_DIR, *sub_path)
        await async_make_dirs(full_path, exist_ok=True)

    tmp_file = os.path.join(full_path, filename)
    return tmp_file


@class_view_swagger_path('/app/swagger/images')
class ImageView(View):

    @classmethod
    async def post(cls, request):
        try:
            reader = await request.multipart()
        except AssertionError as e:
            raise HTTPBadRequest(text=e.args[0])
        async for field in reader:
            if field.filename is None:
                logging.warning(f"Image uploading: {field.name} is not file")
                continue

            # generate a name for the file
            tmp_file = await generate_filename()

            # You cannot rely on Content-Length if transfer is chunked.
            size = 0
            hash_md5 = hashlib.md5()
            async with aiofiles.open(tmp_file, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()  # 8192 bytes by default.
                    if not chunk:
                        break
                    size += len(chunk)
                    await f.write(chunk)
                    hash_md5.update(chunk)

            # check img type
            img_type = imghdr.what(tmp_file)
            if img_type not in ALLOWED_IMG_TYPES:
                await aiofiles.os.remove(tmp_file)
                raise HTTPBadRequest(text=f"Not allowed img type: '{img_type}'")

            # adding .png or .jpeg to the file
            filename = f"{tmp_file}.{img_type}"
            await aiofiles.os.rename(tmp_file, filename)
            data = {
                "url": filename.replace(IMG_DIR, IMG_PATH),
                "size": size,
                "hash": f"md5:{hash_md5.hexdigest()}"
            }
            return {"data": data}
