# Create meta-cache for all files in a DICOM directory
# Upload by accession num

# Redis cache:

# file_name: tag dicts  <- do we even need that?
# accession_num: set of file_names

import glob, os, logging, yaml
import attr
from ..apis import Redis, DicomFile, Orthanc


# Generates 1024 nested subdirs
class orthanc_subdirs(object):

    def __init__(self, base_dir=None, low=0, high=256*256-1):
        self.base_dir = base_dir
        self.current = low
        self.high = high

    def __iter__(self):
        return self

    def __next__(self):  # Python 3: def __next__(self)
        if self.current > self.high:
            raise StopIteration
        else:
            self.current += 1
            hex = '{:04X}'.format(self.current - 1).lower()
            orthanc_dir = os.path.join(self.base_dir, hex[0:2], hex[2:4])
            return orthanc_dir


# Generates subdirs with os.walk, this remains _very_ slow for large datasets!
class unstructured_subdirs(object):

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.generator = os.walk(base_dir)

    def __iter__(self):
        return self

    def __next__(self):  # Python 3: def __next__(self)
        return self.generator.__next__()[0]



@attr.s
class FileIndexer(object):
    location = attr.ib( default=None )
    filehandler = attr.ib( type=DicomFile )

    redis_conf = attr.ib( factory=dict )
    cache = attr.ib( type=Redis )

    @filehandler.default
    def get_filehandler(self):
        return DicomFile(location=self.location)

    @cache.default
    def get_cache(self):
        return Redis(**self.redis_conf)

    def run(self, relpath=None, rex="*.dcm"):

        if relpath:
            basepath=os.path.join(self.location, relpath)
        else:
            basepath=self.location

        for fp in unstructured_subdirs(basepath):
            path = os.path.relpath(fp, self.location)
            logging.debug(path)
            self.index_dir(path, rex)

    def run_orthanc(self, relpath=None):

        if relpath:
            basepath=os.path.join(self.location, relpath)
        else:
            basepath=self.location

        for fp in orthanc_subdirs(basepath):
            path = os.path.relpath(fp, self.location)
            # logging.debug(path)
            self.index_dir(path, rex="*")

    def index_dir(self, path=None, rex="*.dcm"):
        fg = os.path.join(self.location, path, rex )
        # logging.debug(fg)
        # files = glob.glob(fg)

        files = [os.path.basename(x) for x in glob.glob(fg)]
        # logging.debug(files)

        # logging.debug( self.reader.location )

        for fn in files:
            # logging.debug(path)
            # logging.debug(fn)
            try:
                d = self.filehandler.get(fn, path=path, view="tags")
                self.cache.sput(d.meta["AccessionNumber"], d, key="FullPath")
            except:
                pass
                # logging.warning("Skipping non-DICOM file {}".format(fn))

    def find_items_for(self, accession_number):
        logging.debug(accession_number)
        return self.cache.sget(accession_number)


    def put_accession(self, accession_number, dest: Orthanc):

        dixels = self.find_items_for(accession_number)
        for d in dixels:
            # logging.debug(type(d))
            d = self.filehandler.get(d, view="file")
            dest.put(d)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    with open("secrets/lifespan_services.yml") as f:
        services = yaml.safe_load(f)
    redis_conf = services['redis']

    x = FileIndexer(location="/Users/derek/data/DICOM", redis_conf = redis_conf)

    # x.cache.clear()
    # x.run(relpath="anon.chest_abd_pelvis", rex="IM*")  # Has no a/n
    # x.run(relpath="airway phantom", rex="IM*")
    # x.run_orthanc(relpath="Christianson")

    orthanc = Orthanc()
    x.put_accession("rphy10252012", orthanc) # airway phant
    x.put_accession("4758606", orthanc)  # christianson

