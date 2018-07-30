# import logging
# logger = logging.getLogger('Tithonus.Utilities')
# logger.setLevel(logging.DEBUG)
# ch = logging.StreamHandler()
# formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)

# Zip wrapper

import zipfile
import os
import io

def zipdir(top, fno=None):

    file_like_object = None
    if fno is None:
        # logger.info('Creating in-memory zip')
        file_like_object = io.BytesIO()
        zipf = zipfile.ZipFile(file_like_object, 'w', zipfile.ZIP_DEFLATED)
    else:
        # logger.info('Creating in-memory zip')
        zipf = zipfile.ZipFile(fno, 'w', zipfile.ZIP_DEFLATED)

    for dirpath, dirnames, filenames in os.walk(top):
        for f in filenames:
            fn = os.path.join(dirpath, f)
            zipf.write(fn, os.path.relpath(fn, top))

    if fno is None:
        return file_like_object
    else:
        zipf.close()

