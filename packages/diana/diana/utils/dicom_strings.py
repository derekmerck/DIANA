import logging
from datetime import datetime

def dicom_strpdtime( dts: str ) -> datetime:

    logger = logging.getLogger()

    if not dts:
        logger.error("Failed to parse empty date time string")
        ts = datetime.now()
        return ts

    try:
        # GE Scanner dt format
        ts = datetime.strptime( dts , "%Y%m%d%H%M%S")
        return ts
    except ValueError:
        # Wrong format
        pass

    try:
        # Siemens scanners use a slightly different aggregated format with fractional seconds
        ts = datetime.strptime( dts , "%Y%m%d%H%M%S.%f")
        return ts
    except ValueError:
        # Wrong format
        pass

    logger.error("Failed to parse date time string: {0}".format( dts ))
    ts = datetime.now()
    return ts

def dicom_strptime( dts: str) -> datetime:

    return datetime.strptime( dts, "%H%M%S" )

def dicom_strpdate( dts: str) -> datetime.date:

    return datetime.strptime( dts, "%Y%m%d" ).date()


def dicom_strftime( dt: datetime ) -> str:
    """
    datetime -> dicom time
    """
    return dt.strftime( "%Y%m%d%H%M%S" )


def dicom_strfdate( dt: datetime ) -> str:
    """
    datetime -> dicom date
    """
    return dt.strftime( "%Y%m%d" )


def dicom_strftime2( dt: datetime ) -> (str, str):
    """
    datetime -> (dicom date, dicom time)
    """
    return (dt.strftime( "%Y%m%d" ), dt.strftime( "%H%M%S" ))


def dicom_strfname( names: tuple) -> str:
    """
    doe john s -> dicome name (DOE^JOHN^S)
    """
    return "^".join(names)
