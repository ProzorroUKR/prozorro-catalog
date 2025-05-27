from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest
from catalog.settings import IMG_PATH, IMG_DIR, ALLOWED_IMG_TYPES, IMG_SIZE_LIMIT
from catalog.image import monkey_patch_jpeg_tests, generate_filename
import aiofiles
import aiofiles.os
import imghdr
import hashlib
import logging


monkey_patch_jpeg_tests()


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

            # check img size
            if size > IMG_SIZE_LIMIT:
                raise HTTPBadRequest(text=f"Image must be less than {IMG_SIZE_LIMIT} bytes")

            # adding .png or .jpeg to the file
            filename = f"{tmp_file}.{img_type}"
            await aiofiles.os.rename(tmp_file, filename)
            data = {
                "url": filename.replace(IMG_DIR, IMG_PATH),
                "size": size,
                "hash": f"md5:{hash_md5.hexdigest()}"
            }
            return {"data": data}
        raise HTTPBadRequest(text='There are no images')
