import logging
from pprint import pformat
from io import BytesIO
# import json
import datetime
from Gateway import *
from MeasureScout import MeasureScout


def UpdateSeriesIndex( orthanc, splunk, splunk_index='series' ):
    orthanc.level = 'series'
    splunk.index = splunk.index_names[splunk_index]
    items = orthanc.ListItems()

    logging.debug('Candidate items:')
    logging.debug(pprint.pformat(items))

    CopyNewItems( orthanc, splunk, items, 'tags' )

    # def get_remote_study_ids(**kwargs):
    #
    #     study_date = kwargs.get('study_date', '')
    #     study_time = kwargs.get('study_time', '')
    #     modality = kwargs.get('modality', 'CT')
    #     accession_number = kwargs.get('accession_number', '')
    #     retrieve = kwargs.get('retrieve', False)
    #     stuid = kwargs.get('stuid', '')
    #
    #     orthanc.level = 'study'
    #     q = orthanc.QueryRemote(remote, query={'StudyInstanceUID': stuid,
    #                                            'StudyDate': study_date,
    #                                            'StudyTime': study_time,
    #                                            'AccessionNumber': accession_number,
    #                                            'ModalitiesInStudy': modality})
    #
    #     logging.debug("Study level responses")
    #     logging.debug(pprint.pformat(q))
    #
    #     answers = orthanc.session.do_get('queries/{0}/answers/'.format(q['ID']))
    #
    #     stuids = []
    #
    #     # Review all series for this study
    #     for a in answers:
    #         r = orthanc.session.do_get('queries/{0}/answers/{1}/content?simplify'.format(q['ID'], a))
    #         logging.debug(pprint.pformat(r))
    #
    #         stuids.append(r['StudyInstanceUID'])
    #
    #         if retrieve:
    #             r = orthanc.session.do_post('queries/{0}/answers/{1}/retrieve'.format(q['ID'], a), 'DEATHSTAR')
    #             logging.debug(pprint.pformat(r))
    #
    #     return stuids

# Doing this hour-by-hour results in a complete list of studies for the day
# DOES include outside studies
# DOES include incomplete or cancelled studies
# DOES NOT include OFFLINE studies
# This _should_ be more than whatever is in the dose index, as it will include outside studies.

def UpdateRemoteStudyIndex( orthanc, remote, splunk, **kwargs ):
    orthanc.level = 'study'
    splunk.index = splunk.index_names['remote_studies']

    existing_items = splunk.ListItems()
    # logging.debug(existing_items)

    study_date = kwargs.get('study_date')
    study_time = kwargs.get('study_time')
    modality = kwargs.get('modality', 'CT')

    # Have to request all fields that you want returned (see DICOM std table C.6-5)
    q = orthanc.QueryRemote(remote, query={'StudyDate': study_date,
                                           'AccessionNumber':'',
                                           'ModalitiesInStudy':modality,
                                           'PatientBirthDate':'',
                                           'NumberOfSeries':'',
                                           'PatientID':'',
                                           'PatientName':'',
                                           'PatientSex':'',
                                           'ReferringPhysicianName': '',
                                           'StudyTime':study_time,
                                           'StudyDescription':''})
    logging.debug(pprint.pformat(q))

    answers = orthanc.session.do_get('queries/{0}/answers/'.format(q['ID']))

    # logging.debug(pprint.pformat(answers))
    # logging.debug("Found {0} answers".format(len(answers)))

    host = '{0}:{1}/modalities/{2}'.format(orthanc.session.hostname, orthanc.session.port, remote)
    # accessions = []

    for a in answers:
        r = orthanc.session.do_get('queries/{0}/answers/{1}/content?simplify'.format(q['ID'],a))
        r = simplify_tags(r)

        s = hashlib.sha1("{0}{1}".format(str(r['PatientID']), str(r['StudyInstanceUID']))).hexdigest()
        r['ID'] = '-'.join(s[i:i+8] for i in range(0, len(s), 8))

        logging.debug(pprint.pformat(r))

        if not str(r['ID']) in existing_items:
            logging.debug('Adding item {0}'.format(r['ID']))
            splunk.AddItem(r, src=orthanc, host=host)
            # accessions.append(r['AccessionNumber'])
        else:
            logging.debug('Skipping item {0}'.format(r['ID']))

    # logging.debug(accessions)
    # logging.debug("Found {0} studies to index".format(len(accessions)))
    #
    # return len(accessions)


def UpdateRemoteSeriesIndex( orthanc, remote, splunk, **kwargs ):

    # Query the study index to get a list of candidate accession numbers
    # Query the series index to eliminate series that have already been indexed
    # Query remote for each candidate accession number to get basic DICOM tags

    def get_remote_instance_ids(stuid, seruid, retrieve=False):

        orthanc.level = 'instances'
        q = orthanc.QueryRemote(remote, query={'StudyInstanceUID': stuid,
                                               'SeriesInstanceUID': seruid})

        logging.debug("Instance level responses")
        logging.debug(pprint.pformat(q))

        answers = orthanc.session.do_get('queries/{0}/answers/'.format(q['ID']))

        instuids = []

        # Review all instances for this study
        for a in answers:
            r = orthanc.session.do_get('queries/{0}/answers/{1}/content?simplify'.format(q['ID'], a))
            logging.debug(pprint.pformat(r))

            instuid = r['SOPInstanceUID']
            instuids.append(instuid)

            if retrieve:
                r = orthanc.session.do_post('queries/{0}/answers/{1}/retrieve'.format(q['ID'], a), 'DEATHSTAR')

                # r = orthanc.RetrieveFromRemote(remote, resources=[{'StudyInstanceUID': stuid,
                #                                                    'SeriesInstanceUID': seruid,
                #                                                    'SOPInstanceUID': instuid,
                #                                                    'MediaStorageSOPInstanceUID': instuid
                #                                                    }])
                logging.debug(pprint.pformat(r))

        return instuids

    def get_remote_series_ids(stuid, retrieve=False):

        orthanc.level = 'series'
        q = orthanc.QueryRemote(remote, query={'StudyInstanceUID': stuid})

        logging.debug("Series level responses")
        logging.debug(pprint.pformat(q))

        answers = orthanc.session.do_get('queries/{0}/answers/'.format(q['ID']))

        seruids = []

        # Review all studies for these conditions
        for a in answers:
            r = orthanc.session.do_get('queries/{0}/answers/{1}/content?simplify'.format(q['ID'], a))
            logging.debug(pprint.format(r))

            seruids.append(r['SeriesInstanceUID'])

            if retrieve:
                r = orthanc.session.do_post('queries/{0}/answers/{1}/retrieve'.format(q['ID'], a), 'DEATHSTAR')
                logging.debug(pprint.pformat(r))

        return seruids

    def get_remote_study_ids(**kwargs):

        study_date = kwargs.get('study_date', '')
        study_time = kwargs.get('study_time', '')
        modality = kwargs.get('modality', 'CT')
        accession_number = kwargs.get('accession_number', '')
        retrieve = kwargs.get('retrieve', False)
        stuid = kwargs.get('stuid', '')

        orthanc.level = 'study'
        q = orthanc.QueryRemote(remote, query={'StudyInstanceUID': stuid,
                                               'StudyDate': study_date,
                                               'StudyTime': study_time,
                                               'AccessionNumber': accession_number,
                                               'ModalitiesInStudy': modality})

        logging.debug("Study level responses")
        logging.debug(pprint.pformat(q))

        answers = orthanc.session.do_get('queries/{0}/answers/'.format(q['ID']))

        stuids = []
        accessions = []

        # Review all series for this study
        for a in answers:
            r = orthanc.session.do_get('queries/{0}/answers/{1}/content?simplify'.format(q['ID'], a))
            logging.debug(pprint.pformat(r))

            stuids.append(r['StudyInstanceUID'])
            accessions.append(r['AccessionNumber'])

            if retrieve:
                r = orthanc.session.do_post('queries/{0}/answers/{1}/retrieve'.format(q['ID'], a), 'DEATHSTAR')
                logging.debug(pprint.pformat(r))

        return stuids, accessions

    stuids, accessions = get_remote_study_ids(retrieve=False, **kwargs)
    logging.debug(stuids)

    return(accessions[0])

    seruids = get_remote_series_ids(stuids[0])
    logging.debug(seruids)

    for seruid in seruids:
        instuids = get_remote_instance_ids(stuids[0], seruid, retrieve=True)
        logging.debug(instuids)

    # UpdateSeriesIndex(orthanc, splunk, 'remote_series')
    #
    # # Now scrub these studies
    # orthanc.DropAll()



def UpdateDoseReports( orthanc, splunk ):

    # List of candidate series out of Splunk/dicom_series
    splunk.index = splunk.index_names['series']
    # Can limit the search with "earliest=-2d" for example
    q = "search earliest=-2d index={0} SeriesNumber = 997 OR SeriesNumber = 502 OR SeriesNumber = 9001 OR (SeriesNumber > 65500 AND SeriesNumber < 65600) | table ID".format(splunk.index)
    logging.warning(q)
    candidates = splunk.ListItems(q)

    # Which ones are already available in Splunk/dose_records (looking at ParentSeriesID)
    splunk.index = splunk.index_names['dose']
    q = "search earliest-2d index={0} | table ParentSeriesID".format(splunk.index)
    logging.warning(q)
    indexed = splunk.ListItems(q)

    items = SetDiff(candidates, indexed)

    # logging.debug(pprint.pformat(candidates))
    # logging.debug(pprint.pformat(indexed))
    # logging.debug(pprint.pformat(items))

    # Get instance from Orthanc
    for item in items:
        orthanc.level = 'series'
        info = orthanc.GetItem(item, 'info')
        instance = info['Instances'][0]

        orthanc.level = 'instances'
        tags = orthanc.GetItem(instance, 'tags')
        # Add IDs
        tags['ParentSeriesID'] = item

        # Normalize missing CTDIvol tags
        tags = normalize_ctdi_tags(tags)

        logging.debug(pprint.pformat(tags))

        splunk.AddItem(tags, src=orthanc)

    logging.debug('Candidate dose reports: {0}'.format(len(candidates)))
    logging.debug('Indexed dose reports: {0}'.format(len(indexed)))
    logging.debug('New dose reports: {0}'.format(len(items)))


def UpdatePatientDimensions( orthanc, splunk ):
    '''Queries Splunk for unsized localizers and measures them'''

    # List of candidate series out of Splunk/dicom_series
    splunk.index = splunk.index_names['series']
    # Can limit the search with "earliest=-2d" for example
    q = "search index={0} Modality=CT ImageType=\"*LOCALIZER*\" | table AccessionNumber SeriesNumber ID | join type=left [search index=patient_dims | table AccessionNumber AP_dim lateral_dim ] | where isnull(AP_dim) | fields - AccessionNumber SeriesNumber AP_dim".format(splunk.index)
    items = splunk.ListItems(q)

    for i in range(0,len(items)):
        items[i] = items[i].replace(',', '')

    logging.debug(pformat(items))

    # Get instance from Orthanc
    for item in items:
        orthanc.level = 'series'
        info = orthanc.GetItem(item, 'info')

        logging.debug(info)

        orthanc.level = 'instances'
        for instance in info['Instances']:

            data = orthanc.GetItem(instance, 'file')

            ret = MeasureScout(BytesIO(data))

            logging.debug(pformat(ret))
            ret["ID"] = instance
            ret["InstanceCreationDateTime"] = datetime.datetime.now()

            splunk.index = splunk.index_names['patient_dims']
            splunk.AddItem(ret, src=orthanc)


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)

    orthanc0_address = "http://orthanc:orthanc@localhost:8042"
    orthanc1_address = "http://orthanc:orthanc@localhost:8043"
    splunk_address   = "https://admin:splunk@localhost:8089"
    hec_address      = "http://Splunk:token@localhost:8088"

    splunk = SplunkGateway(address=splunk_address,
                           hec_address=hec_address)
    orthanc0 = OrthancGateway(address=orthanc0_address)
    orthanc1 = OrthancGateway(address=orthanc1_address)

    # Update the series index
    UpdateSeriesIndex(orthanc0, splunk)

    # Update the dose reports based on the splunk index
    UpdateDoseReports(orthanc0, splunk)
