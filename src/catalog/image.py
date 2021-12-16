from catalog.settings import IMG_DIR, IMG_STORE_DIR_NAME_LEN, IMG_STORE_DIR_LEVELS
import aiofiles.os
from os import makedirs
from uuid import uuid4
from imghdr import tests
import os.path


def test_jpeg1(h, f):
    """JPEG data in JFIF format"""
    if b'JFIF' in h[:23]:
        return 'jpeg'


JPEG_MARK = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06' \
            b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'


def test_jpeg2(h, f):
    """JPEG with small header"""
    if len(h) >= 32 and 67 == h[5] and h[:32] == JPEG_MARK:
        return 'jpeg'


def test_jpeg3(h, f):
    """JPEG data in JFIF or Exif format"""
    if h[6:10] in (b'JFIF', b'Exif') or h[:2] == b'\xff\xd8':
        return 'jpeg'


def monkey_patch_jpeg_tests():
    """
    Extends check  imghdr.what(name)
    https://bugs.python.org/issue28591
    :return:
    """
    tests.append(test_jpeg1)
    tests.append(test_jpeg2)
    tests.append(test_jpeg3)


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
