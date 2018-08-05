# Diana-agnostic DICOM info

import logging, functools
from enum import Enum
from hashlib import sha1
from datetime import datetime
import attr

logger = logging.getLogger(__name__)


# @functools.total_ordering
class DicomLevel(Enum):
    PATIENTS  = 0
    STUDIES   = 1
    SERIES    = 2
    INSTANCES = 3

    # Provides a partial ordering so they are comparable
    # Note that Study < Instance under this order
    # def __eq__(self, other):
    #     if self.__class__ is other.__class__:
    #         # logging.debug("{}<{}".format(self.value, other.value))
    #         return self.value == other.value
    #     return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            # logging.debug("{}<{}".format(self.value, other.value))
            return self.value < other.value
        return NotImplemented

    @classmethod
    def of(cls, value: str):
        if value.lower()=="instances":
            return DicomLevel.INSTANCES
        elif value.lower()=="series":
            return DicomLevel.SERIES
        elif value.lower()=="studies":
            return DicomLevel.STUDIES

        return DicomLevel.PATIENTS

    def parent_level(self):
        if self == DicomLevel.PATIENTS:
            raise ValueError
        return DicomLevel( int(self.value) + 1 )

    def child_level(self):
        if self == DicomLevel.INSTANCES:
            raise ValueError
        return DicomLevel( int(self.value) - 1 )

    def __str__(self):
        return '{0}'.format(self.name.lower())

