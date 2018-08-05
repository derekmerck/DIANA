# Diana-agnostic Dicom file reading and writing

import logging, os
from typing import Sequence
import attr
import pydicom
import binascii
from PIL.Image import fromarray

@attr.s
class FileHandler(object):
    location = attr.ib(default="")
    logger = attr.ib(init=False)

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def fp(self, fn: str, path: str=None, explode: Sequence=None):
        partial = None
        if self.location:
            partial = self.location
        if path:
            # logging.debug(self.location)
            # logging.debug(partial)
            # logging.debug(path)
            partial = os.path.join(partial, path)
        if explode:
            epath = self.explode_path(fn, explode[0], explode[1])
            partial = os.path.join(partial, epath)

        if partial:
            fp = os.path.join(partial, fn)
            return fp

        return fn

    def explode_path(self, fn: str, stride: int, depth: int):
        expath = []
        for i in range(depth):
            block = fn[(i*stride) : (i+1)*stride]
            # self.logger.debug("Block: {}".format(block))
            expath.append(block)
        return os.path.join(*expath)

    def remove(self, fn: str, path: str=None):
        fp = self.fp(fn, path)
        os.remove( fp )


@attr.s
class ImageFile(FileHandler):

    def write(self, fn: str, data, path: str=None, explode: Sequence=None):
        fp = self.fp(fn, path, explode)

        if not os.path.dirname(fn):
            os.makedirs(os.path.dirname(fn))

        im = fromarray(data)
        im.save(fp)


@attr.s
class TextFile(FileHandler):

    def write(self, fn: str, data: str, path: str=None, explode: Sequence=None):
        fp = self.fp(fn, path, explode)

        if not os.path.dirname(fn):
            os.makedirs(os.path.dirname(fn))

        with open(fp, 'w') as f:
            f.write(data)

    def read(self, *args, **kwargs):
        # There is really not much need to read from a file-by-file text corpus into Dixels
        raise NotImplementedError


@attr.s
class DicomFile(FileHandler):

    def exists(self, fn: str, path: str, explode: Sequence=None) -> bool:
        fp = self.fp(fn, path, explode)
        return os.path.isfile(fp)

    def write(self, fn: str, data, path: str, explode: Sequence=None):
        fp = self.fp(fn, path, explode)
        self.logger.debug("Writing {}".format(fp))

        if not os.path.isdir( os.path.dirname(fp) ):
            self.logger.debug("Creating dir tree for {}".format( os.path.dirname(fp) ))
            os.makedirs(os.path.dirname(fp))

        with open(fp, 'wb+') as f:
            f.write(data)

    def read(self, fn: str, path: str=None, explode: Sequence=None, pixels: bool=False):
        fp = self.fp(fn, path, explode)
        self.logger.debug("Reading {}".format(fp))

        def is_dicom(fp):
            try:
                with open(fp, 'rb') as f:
                    f.seek(0x80)
                    header = f.read(4)
                    magic = binascii.hexlify(header)
                    if magic == b"4449434d":
                        # self.logger.debug("{} is dcm".format(fp))
                        return True
            except:
                pass

            self.logger.error("{} is NOT dcm".format(fp))
            return False

        if not is_dicom(fp):
            raise Exception("Not a DCM file: {}".format(fp))

        if not pixels:
            dcm = pydicom.read_file(fp, stop_before_pixels=True)
        else:
            dcm = pydicom.read_file(fp)

        return dcm, fp
