"""
Diana CT Dose Report Harvester
Merck, Summer 2018

Relatively generic implementation: finds all recent SR series from CT
studies and copies anything new to Splunk.  Replace `discover_recent`
with more complex discrimination if necessary.
"""

import logging
import attr
from ..utils.dicom import DicomLevel
from .harvester import Harvester


@attr.s
class DoseReportHarvester(Harvester):

    """
    discover indexed = splunk.find
    discover available = orthanc.find

    worklist = i - a

    for item in worklist:
      - get item | send splunk

    """

    def discover_recent(self):

        q = {"StudyDate": self.time_window.as_dicom2()[0][0],
             "StudyTime": "{}-{}".format( self.time_window.as_dicom2()[0][1],
                                          self.time_window.as_dicom2()[1][1] ),
             "StudyDescription": '',
             "ModalitiesInStudy": "CT"}
        recent_ct_studies = self.source.find(q, DicomLevel.STUDIES, self.source_domain)

        if not recent_ct_studies:
            return

        q = {"StudyDate": self.time_window.as_dicom2()[0][0],
             "StudyTime": "{}-{}".format( self.time_window.as_dicom2()[0][1],
                                          self.time_window.as_dicom2()[1][1] ),
             "SeriesDescription": '',
             "Modality": "SR"}

        recent_sr_series = self.source.find(q, DicomLevel.SERIES, self.source_domain)

        if not recent_sr_series:
            return

        recent_ctsr_series = set()

        # Candidates = any SR series from a CT study
        for item in recent_sr_series:
            if item.AccessionNumber in [item.AccessionNumber for item in recent_ct_studies]:
                recent_ctsr_series.add(item)

        logging.info("Found {} items from {}-{}".format(len(recent_ctsr_series), *self.time_window.as_dicom2()))

        return recent_ctsr_series

    def discover_indexed(self):

        q = "search index={} | dedup AccessionNumber".format(self.dest_domain, self.source.location)
        indexed = self.dest.find_items(q, time_interval=self.time_window)
        return indexed

    def handle_worklist(self, worklist):

        # logging.debug(worklist)

        for series in worklist:

            desc = "{} at {} ({})".format(series.meta['AccessionNumber'],
                                              # series.meta['StudyDescription'],
                                              series.meta['StudyTime'],
                                              series.meta['SeriesDescription'])
            logging.info(desc)

            q = {"StudyInstanceUID": series.meta["StudyInstanceUID"],
                 "SeriesInstanceUID": series.meta["SeriesInstanceUID"]}

            ret = self.source.find(q, DicomLevel.SERIES, self.source_domain, retrieve=True)
            d = self.source.get(series.oid(), level=DicomLevel.SERIES, view="instance_tags")
            self.dest.put(d, index=self.dest_domain, host=self.source.location, hec=self.dest_domain)
            self.source.remove(d)
