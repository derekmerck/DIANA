
import logging
from diana.utils.dtinterval import test_timerange
from diana.utils.dicom.dicom_simplify import test_simplify

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_timerange()
    test_simplify()

