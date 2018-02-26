from SessionWrapper import Session
from StructuredTags import simplify_tags, normalize_ctdi_tags
import collections
import logging
from bs4 import BeautifulSoup
import time
import pprint
import hashlib

class Gateway(object):

    def __init__(self, *args, **kwargs):
        super(Gateway, self).__init__()
        # Create session wrapper
        address = kwargs.get('address')
        self.session = Session(address)

    def ListItems(self, condition=None, *args, **kwargs):
        raise NotImplementedError

    def GetItem(self, *args, **kwargs):
        raise NotImplementedError

    def AddItem(self, item, *args, **kwargs):
        raise NotImplementedError


class OrthancGateway(Gateway):

    def __init__(self, *args, **kwargs):
        super(OrthancGateway, self).__init__(**kwargs)
        # Active level
        self.level = kwargs.get('level')

    def QueryRemote(self, remote, query=None, *args, **kwargs):

        data = {'Level': self.level,
                'Query': query}

        r = self.session.do_post('modalities/{0}/query'.format(remote), data=data)
        return r

    def RetrieveFromRemote(self, remote, resources=None):
        data = {'Level': self.level,
                'Resources': resources}

        logging.debug(pprint.pformat(data))

        r = self.session.do_post('modalities/{0}/move'.format(remote), data=data)

        return r

    def ListItems(self, condition=None, *args, **kwargs):

        if condition:
            raise NotImplementedError

        r = self.session.do_get(self.level)
        logging.info("Found {0} candidate {1}.".format(len(r), self.level))
        return r

    def DropAll(self):
        self.level = 'patients'
        items = self.ListItems()
        for item in items:
            self.DeleteItem(item)

    def DeleteItem(self, item):
        self.session.do_delete('{0}/{1}'.format(self.level, item))

    def GetItem(self, item, dtype="tags"):

        r = None
        if dtype=="tags":
            if self.level == 'instances':
                r = self.session.do_get('{0}/{1}/tags?simplify'.format(self.level, item))
            else:
                r = self.session.do_get('{0}/{1}/shared-tags?simplify'.format(self.level, item))

            r = simplify_tags(r)
            # Add item ID for later reference
            r['ID'] = item

            # logging.debug(pprint.pformat(r))

        elif dtype=="info":
            r = self.session.do_get('{0}/{1}'.format(self.level, item))

        elif dtype=="file":
            r = self.session.do_get('{0}/{1}/file'.format(self.level, item))
        return r

    def AddItem(self, item, *args, **kwargs):
        if self.level != "instances":
            raise NotImplementedError
        headers = {'content-type': 'application/dicom'}
        self.session.do_post('instances', data=item, headers=headers)


class SplunkGateway(Gateway):

    def __init__(self, *args, **kwargs):
        super(SplunkGateway, self).__init__(**kwargs)
        self.hec_address = kwargs.get('hec_address')
        if self.hec_address:
            self.hec = Session(self.hec_address)
        # Active index name
        self.index = kwargs.get('index')
        # Mapping between functions and index names
        self.index_names = kwargs.get('index_names',
                                      {'series': 'dicom_series',
                                       'dose': 'dose_reports',
                                       'remote_studies': 'pacs_studies',
                                       'remote_series': 'pacs_series',
                                       'patient_dims': 'patient_dims'})

    def ListItems(self, condition=None, *args, **kwargs):

        def poll_until_done(sid):
            isDone = False
            i = 0
            r = None
            while not isDone:
                i = i + 1
                time.sleep(1)
                r = self.session.do_get('services/search/jobs/{0}'.format(sid), params={'output_mode': 'json'})
                isDone = r['entry'][0]['content']['isDone']
                status = r['entry'][0]['content']['dispatchState']
                if i % 5 == 1:
                    logging.debug('Waiting to finish {0} ({1})'.format(i, status))
            return r['entry'][0]['content']['resultCount']

        if not condition:
            condition = "search index={0} | spath ID | dedup ID | table ID".format(self.index)

        r = self.session.do_post('services/search/jobs', data="search={0}".format(condition))
        soup = BeautifulSoup(r, 'xml')
        sid = soup.find('sid').string
        n = poll_until_done(sid)
        offset = 0
        instances = []
        i = 0
        while offset < n:
            count = 50000
            offset = 0 + count * i
            r = self.session.do_get('services/search/jobs/{0}/results'.format(sid),
                             params={'output_mode': 'csv', 'count': count, 'offset': offset})
            instances = instances + r.replace('"', '').splitlines()[1:]
            i = i + 1
        return instances

    def AddItem(self, item, *args, **kwargs):

        def epoch(dt):
            tt = dt.timetuple()
            return time.mktime(tt)

        src = kwargs.get('src')
        host = kwargs.get('host', '{0}:{1}'.format(src.session.hostname, src.session.port))

        data = collections.OrderedDict([('time', epoch(item['InstanceCreationDateTime'])),
                                        ('host', host),
                                        ('sourcetype', '_json'),
                                        ('index', self.index),
                                        ('event', item)])
        # logging.debug(pformat(data))
        self.hec.do_post('services/collector/event', data=data)


def SetDiff( items1, items2 ):
    if not items2:
        return items1
    return set(items1) - set(items2)


def CopyItems( src, dest, items, dtype='tags' ):

    if not items:
        logging.info('Nothing to copy')
        return

    logging.debug('Items to copy:')
    logging.debug(pprint.pformat(items))

    for item in items:
        data = src.GetItem(item, dtype)
        dest.AddItem(data, src=src)


def CopyNewItems( src, dest, items, dtype='tags' ):
    new_items = SetDiff(items, dest.ListItems() )

    logging.debug('New items:')
    logging.debug(pprint.pformat(new_items))

    CopyItems(src, dest, new_items, dtype)



if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

