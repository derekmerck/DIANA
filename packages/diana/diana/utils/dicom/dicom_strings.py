import logging, re
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


def dicom_patient_initials( names: str ) -> str:
    """
    "DOE^JOHN^B"  -> "JBD"
    "Doe, John B" -> "JBD"
    "john b doe"  -> "JBD"
    "John Doe"    -> "JD"
    "doe, john"   -> "JD"
    "doe"         -> "D"
    "subject 1"   -> "ID 1"
    "subject 102" -> "ID 102"
    "subject ab102ab102" -> "ID ab102ab102"
    """

    if not names:
        return

    names = "{}".format(names)

    # Does it have a number
    match = re.findall(r"\w*\d+\w*", names)
    if match:
        # It's a numeric ID
        return "ID {}".format(match[0])

    # DICOM is in "last, first initial" format
    names = names.replace("^", ", ")

    l = []
    for word in names.split():
        part = word[0].upper()
        l += part

    if names.find(",") >= 0:
        l = l[1:] + l[:1]
    return "".join(l)


###################
# TESTS
###################

def test_patient_initials():
    names = {
        "DOE^JOHN^B": "JBD",
        "Doe, John B": "JBD",
        "john b doe": "JBD",
        "John Doe": "JD",
        "doe, john": "JD",
        "doe": "D",
        "subject 1": "ID 1",
        "subject 102": "ID 102",
        "subject ab102ab102": "ID ab102ab102",
        "run off, aortic": "ARO"
    }

    for k, v in names.items():
        assert (dicom_patient_initials(k) == v)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_patient_initials()