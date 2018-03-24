"""
TODO: When a specific AN is requested, lookup any file, figure out the
TODO: SERUID and series OID, check which instances exist for ONLY
TODO: that study -- this would be so much faster!

DCM Dir Indexer
Merck, Winter 2018

Occasionally, postgres containers will fail or orthanc db folders
have to be migrated from one node to another, which requires
rebuilding the postgres database.

Indexing and/or uploding very large DICOM directories (>20M slices!)
is hugely time consuming, and inevitable crashes require starting
over from scratch re-reading files to figure out if they are already
indexed or need to be re-uploaded.

`ddindex.py` uses a Redis cache to pre-index enough information about
each file to compute it's OID and Accession membership without needing to
reread the original file.  Once the dcm directory is pre-indexed, it can be
partially uploaded, and then resumed later from the same spot with minimal
overhead from verifying the pre-index.  If the pre-index cache is known to
be complete, this can be skipped entirely. Uploading is then just a matter
of comparing every entry in the cache to Orthanc's instance manifest and
uploading the missing items.

Because pre-indexing and uploading is an I/O bound task, it can be sped up
with multiprocessing. Several different task generators allow for simple
asynchronous processing pooling.

Usage:

# Build pre-index cache of /orthanc/db using services enumerated in `secrets.yml`
$ python ddindex.py --workers 8 --config_file secrets.yml \
> --redis_svc dev:redis --orthanc_svc dev:orthanc /orthanc/db

# Skip pre-index verification and upload the accession number XYZ to orthanc
$ python ddindex.py -c secrets.yml -r dev:redis -o dev:orthanc -p --accession XYZ /orthanc/db

# Verify the pre-index cache and compress and upload all files to orthanc
$ python ddindex.py -c secrets.yml -r dev:redis -o dev:orthanc -z --all /orthanc/db

Benchmarks:

8 workers/SSD/3.8GB/11569 files

INFO:root:-----------------------------------
INFO:root:DCM Directory Pre-Indexer
INFO:root:-----------------------------------
INFO:root:  Workers:      8
INFO:root:  Dir:          /Users/derek/Desktop/Christianson
INFO:root:  Time:         21.9230430126 sec
INFO:root:  Num indexed:  11569
INFO:root:  Num/sec:      527.709588187
INFO:root:  Hrs for 40M:  21.0553519584  <-- 21 hours to pre-index the CIRR
INFO:root:-----------------------------------
INFO:root:DCM Pre-Index File Uploader
INFO:root:-----------------------------------
INFO:root:  Workers:      8
INFO:root:  Upload:       All data
INFO:root:  Time:         187.432037115 sec
INFO:root:  Num uploaded: 11569
INFO:root:  Num/sec:      61.7237062461
INFO:root:  Hrs for 40M:  180.013673625
INFO:root:  MB uploaded:  3648.0
INFO:root:  MB/sec:       19.4630547485
INFO:root:  Hrs for 15TB: 214.080817246  <-- 214 hours to upload uncompressed ~9 days
INFO:root:-----------------------------------

INFO:root:-----------------------------------
INFO:root:DCM Directory Pre-Indexer
INFO:root:-----------------------------------
INFO:root:  Workers:      8
INFO:root:  Dir:          /Users/derek/Desktop/Christianson
INFO:root:  Time:         4.14105415344 sec
INFO:root:  Num indexed:  11569
INFO:root:  Num/sec:      2793.73308615
INFO:root:  Hrs for 40M:  3.97715557231   <-- 4 hours to verify CIRR cache (I was seeing like 20 mins before)
INFO:root:-----------------------------------
INFO:root:DCM Pre-Index File Uploader
INFO:root:-----------------------------------
INFO:root:  Workers:      8
INFO:root:  J2K Compression ON
INFO:root:  Upload:       All data
INFO:root:  Time:         242.296519041 sec
INFO:root:  Num uploaded: 11566
INFO:root:  Num/sec:      47.7348995593
INFO:root:  Hrs for 40M:  232.767036564
INFO:root:  MB uploaded:  2082.0           <-- Lots of MRs here, so not a good sample, about 1.6GB less
INFO:root:  Num/sec:      8.59277718161
INFO:root:  Hrs for 15TB: 484.903376243    <-- About 2x as long ~ 20 days
INFO:root:-----------------------------------

Uses DianaFuture

"""

import os
import logging
from pprint import pformat
from multiprocessing import Pool
from argparse import ArgumentParser
import yaml
from dcache import RedisCache
from dixel import Dixel, DLVL
from dapi import Orthanc
from pytictoc import TicToc


# Generates 1024 nested subdirs
class orthanc_subdirs(object):

    def __init__(self, base_dir=None, low=0, high=256*256-1):
        self.base_dir = base_dir
        self.current = low
        self.high = high

    def __iter__(self):
        return self

    def next(self):  # Python 3: def __next__(self)
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

    def next(self):  # Python 3: def __next__(self)
        return self.generator.next()[0]


def index_dcm_dir(dcm_dir):
    global R, Q
    file_cache = R
    accession_cache = Q
    # worklist = set()
    n = 0
    for root, dirs, files in os.walk(dcm_dir):
        for name in files:
            # Ignore junk files
            if name.startswith("."):
                continue
            n = n+1
            fp = os.path.join(root, name)
            # logging.debug(fp)
            #ETAFF
            try:
                # Create an instance dixel with a fp key
                d = Dixel(fp, cache=file_cache, init_fn=Dixel.read_dcm, dlvl=DLVL.INSTANCES)
                accession_num = d.data['AccessionNumber']
                accession_cache.sadd(accession_num, fp)
                # worklist.add(d)
            except Exception, e:
                # logging.debug(e.message)
                pass


def index_dcm_dirs(dirs, workers):

    pool = Pool(processes=workers)
    # 1 workers = 64 seconds, 8 workers = 18 seconds (quiet)/21 sec (logged)

    logging.info("-----------------------------------")
    logging.info("DCM Directory Pre-Indexer")
    logging.info("-----------------------------------")
    logging.info("  Workers:      {}".format(workers))
    logging.info("  Dir:          {}".format(s.base_dir))

    t = TicToc()
    t.tic()

    pool.map(index_dcm_dir, dirs)

    toc_ = float( t.tocvalue() )
    n_per_sec = float(len(R)) / toc_
    time40m = 40000000.0 / (n_per_sec or 1) / 60 / 60

    logging.info("  Time:         {} sec".format(toc_))
    logging.info("  Num indexed:  {}".format(len(R)))
    logging.info("  Num/sec:      {}".format(n_per_sec))
    logging.info("  Hrs for 40M:  {}".format(time40m))

def upload_dcm_file(fp):
    global orthanc, R, compress, instance_manifest
    try:
        # Create a ro dixel (skips persisting calls)
        d = Dixel(key=fp, cache=R, ro=True)
    except ValueError:
        # Couldn't create dixel from cache for some reason, fall back to reindex it
        logging.warning('Trying to index rogue fp {}'.format(fp))
        d = Dixel(key=fp, cache=R, init_fn=Dixel.read_dcm, dlvl=DLVL.INSTANCES)
        accession_num = d.data['AccessionNumber']
        Q.sadd(accession_num, fp)

    # logging.debug(instance_manifest)

    if not instance_manifest or d.oid() not in instance_manifest:
        logging.debug("Putting: {}".format(fp))
        orthanc.add(d, compress=compress, lazy=False)  # Implemented MT lazy here
    else:
        logging.debug("Ignoring: {}".format(fp))

def upload_dcm_files(workers, accession_number=None):
    global R, instance_manifest, compress

    pool = Pool(processes=workers)
    initial_size = orthanc.size()
    instance_manifest = orthanc.do_get('instances')
    initial_count = len(instance_manifest)

    logging.info("-----------------------------------")
    logging.info("DCM Pre-Index File Uploader")
    logging.info("-----------------------------------")
    logging.info("  Workers:      {}".format(workers))

    if compress:
        logging.info("  J2K Compress: ON")

    t = TicToc()
    t.tic()

    if accession_number:
        # Upload single accession
        fps = Q.sget(accession_number)
        logging.info("  Upload:       Accession {}".format(accession_number))
    else:
        # Upload _all_
        fps = R.keys()
        logging.info("  Upload:       All data")

    pool.map(upload_dcm_file, fps, 20)

    toc_ = float( t.tocvalue() )

    final_size = orthanc.size()
    instance_manifest = orthanc.do_get('instances')
    final_count = len(instance_manifest)

    count = final_count - initial_count
    upload_mb = final_size - initial_size

    n_per_sec = float(count) / toc_
    time40m = 40000000.0 / (n_per_sec or 1) / 60 / 60

    mb_per_sec = float(upload_mb) / toc_
    time15t = 15000000.0 / (mb_per_sec or 1) / 60 / 60

    logging.info("  Time:         {} sec".format(toc_))
    logging.info("  Num uploaded: {}".format(count))
    logging.info("  Num/sec:      {}".format(n_per_sec))
    logging.info("  Hrs for 40M:  {}".format(time40m))
    logging.info("  MB uploaded:  {}".format(upload_mb))
    logging.info("  MB/sec:       {}".format(mb_per_sec))
    logging.info("  Hrs for 15TB: {}".format(time15t))
    logging.info("-----------------------------------")


def parse_args():

    p = ArgumentParser()

    p.add_argument('--services', '-s',  default='secrets.yml', help="Services config file")
    p.add_argument('--redis', '-r',     default='services:dev:redis',   help="Redis config section path")
    p.add_argument('--orthanc', '-o',   default='services:dev:orthanc', help="Orthanc config section path (req for upload")

    p.add_argument('--workers', '-w',   default=8, type=int, help='Number of workers in threading pool')

    p.add_argument('directory',         )  # Perhaps no directory = pre-indexed?
    p.add_argument('--unstructured',    action= 'store_true',  help="Not an orthanc structured db (slow walk)")
    p.add_argument('--preindexed', '-p',action= 'store_true',  help="Assume pre-index is clean and skip caching")

    p.add_argument('--all',             action= 'store_true',  help="Bulk upload entire directory")
    p.add_argument('--accession',       default=None,          help="Upload an individual accession number")
    p.add_argument('--compress', '-z',  action= 'store_true',  help="Use JPG2K when uploading")
    p.add_argument('--version',         action='version')
    p.add_argument('--verbose', '-v',   action='count',        help="Set output level v/vv")

    opts = p.parse_args()

    def deep_get(d, keys):
        # logging.debug(keys)
        v = d
        for k in keys:
            v = v.get(k)
        return v or {}

    with open(opts.services, 'rU') as f:
        service_config = yaml.load(f)

    redis_kwargs = deep_get(service_config, opts.__dict__['redis'].split(":"))
    opts.__setattr__('redis', redis_kwargs)

    orthanc_kwargs = deep_get(service_config, opts.__dict__['orthanc'].split(":"))
    opts.__setattr__('orthanc', orthanc_kwargs)

    return opts


if __name__ == "__main__":

    # logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    # opts.verbose = None

    if not opts.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level)

    db_files = 14
    db_accessions = 13

    workers       = opts.workers
    directory     = opts.directory
    unstructured  = opts.unstructured
    preindexed    = opts.preindexed
    accession     = opts.accession
    all           = opts.all
    compress      = opts.compress

    # # Overrides for testing...
    # workers       = 8
    # directory     = "/Users/derek/Desktop/Christianson"
    # unstructured  = False
    # preindexed    = False
    # # accession     = 'A2954207'
    # all           = True
    # compress      = True

    CLEAR_R       = False
    CLEAR_Q       = False
    CLEAR_O       = False

    R = RedisCache(db=db_files, clear=CLEAR_R, **opts.redis)
    Q = RedisCache(db=db_accessions, clear=CLEAR_Q, **opts.redis)

    # Confirm the file cache unless it is indicated as pre-indexed
    if not preindexed:
        if not opts.unstructured:
            s = orthanc_subdirs(directory)
        else:
            s = unstructured_subdirs(directory)
        index_dcm_dirs(s, workers)

    # Skip upload unless a specific target is provided
    if accession or all:
        orthanc = Orthanc(clear=CLEAR_O, **opts.orthanc)
        instance_manifest = orthanc.do_get("instances")
        upload_dcm_files(workers, accession_number=accession)




