# Requirements:
#    gdcm for compression       `brew install gdcm` on OSX
#    libmagic for file typing   `brew install libmagic` on OSX

import os
import magic
import dicom
import itertools
from hashlib import sha1
import subprocess

from Dixel import *
from DixelStorage import *
import DixelTools
from Orthanc import Orthanc

class FileStorage(DixelStorage):

    def __init__(self,
                 loc,
                 cache_policy=CachePolicy.USE_CACHE):
        self.loc = loc
        cache_pik = "{0}.pik".format(sha1(self.loc).hexdigest()[0:8])
        super(FileStorage, self).__init__(cache_pik=cache_pik, cache_policy=cache_policy)

    # Mapping from orthanc file_uuid's to directory paths
    def orthanc_path(self, file_uuid):
        ipath = os.path.join(self.loc, file_uuid[0:2], file_uuid[2:4], file_uuid)
        if os.path.isfile(ipath):
            return ipath
        return False

    def initialize_preinventory(self):
        self.logger.debug('Walking file tree')
        all_paths = []
        all_files = []
        for paths, _, files in os.walk(self.loc):
            all_paths = all_paths + list(itertools.repeat(paths, times=len(files)))
            all_files = all_files + files

        preinventory = set()

        for path, fn in zip(all_paths, all_files):
            full_path = os.path.join(path, fn)

            id = full_path
            meta = {'fn': fn,
                    'path': path,
                    'full_path': full_path}

            preinventory.add(Dixel(id, meta=meta))

        # self.logger.debug(preinventory)

        return preinventory

    @property
    def preinventory(self):
        # Force caching
        return self.check_cache('preinventory')

    def initialize_inventory(self):

        # Get predixel file data
        preinventory = self.preinventory

        # Update predixels
        return self.update_worklist(preinventory)

    def update(self, dixel):

        magic_type = magic.from_file(dixel.meta['full_path'], mime=True)
        if magic_type == 'application/dicom':

            tags = dicom.read_file(dixel.meta['full_path'])
            # self.logger.debug(tags)

            meta = { 'PatientID'         : tags[0x0010, 0x0020].value,
                     'StudyInstanceUID'  : tags[0x0020, 0x000d].value,
                     'SeriesInstanceUID' : tags[0x0020, 0x000e].value,
                     'SOPInstanceUID'    : tags[0x0008, 0x0018].value,
                     'TransferSyntaxUID' : tags.file_meta.TransferSyntaxUID,
                     'MediaStorage'      : tags.file_meta.MediaStorageSOPClassUID,
                     'AccessionNumber'   : tags[0x0008, 0x0050].value,
                     'HasPixels'         : 'PixelData' in tags
                    }

            try:
                meta['Dimensions']=[tags[0x0028, 0x0010].value, tags[0x0028, 0x0011].value]
            except KeyError:
                pass

            meta['id'] = DixelTools.orthanc_id(meta['PatientID'],
                                       meta['StudyInstanceUID'],
                                       meta['SeriesInstanceUID'],
                                       meta['SOPInstanceUID'])

            # Keep other meta data, such as file path
            meta.update(dixel.meta)

            self.logger.debug('{0} ({1}) id: {2}'.format(dixel.meta['fn'], magic_type, meta['id']))

            return Dixel(meta['id'], meta=meta, level=DicomLevel.INSTANCES)


    def copy(self, dixel, dest):
        # May have various tasks to do, like anonymize or compress

        if type(dest) == Orthanc and dixel.level == DicomLevel.INSTANCES:

            # Check to confirm that this instance:
            #   1. Has pixels (not an SR)
            #   2. Is value/representation
            #   3. That each dimension is divisible by 8 (square doesn't matter?)
            #   4. Throw out SR and Secondary just in case (shouldn't reach that condition)
            if dest.prefer_compressed and \
                    dixel.meta['HasPixels'] and \
                    int(dixel.meta['Dimensions'][0]) % 8 == 0 and \
                    int(dixel.meta['Dimensions'][1]) % 8 == 0 and \
                    "VR" in str(dixel.meta['TransferSyntaxUID']) and \
                    "SR" not in str(dixel.meta['MediaStorage']) and \
                    "Secondary" not in str(dixel.meta['MediaStorage']):

                self.logger.debug('Compressing {}'.format(dixel.meta['fn']))

                # Compress w gdcm
                full_pathz = "/tmp/{}.compressed".format(dixel.meta['fn'])
                subprocess.call(['gdcmconv', '-U', '--j2k', dixel.meta['full_path'], full_pathz])
                with open(full_pathz, "rb") as f:
                    dixel.data['file'] = f.read()
                os.remove(full_pathz)

            else:

                self.logger.debug('NOT compressing {}'.format(dixel.meta['fn']))

                with open(dixel.meta['full_path'], "rb") as f:
                    dixel.data['file'] = f.read()

            dest.put(dixel)
            dixel.data['file'] = None  # Clear data

        else:
            raise NotImplementedError(
                "{} doesn't know how to put dixel {} into {}".format(
                    self.__class__.__name__,
                    dixel.level,
                    dest.__class__.__name__))

