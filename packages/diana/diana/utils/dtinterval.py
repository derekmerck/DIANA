import logging, re
from datetime import datetime, timedelta
from typing import Union
from dateutil import parser as dtparser
import attr
from .dicom import dicom_strftime, dicom_strftime2


def parse_timestr(time_str: Union[str, datetime]) -> Union[datetime, timedelta, None]:

    if not time_str:
        return

    if type( time_str ) == datetime or type( time_str ) == timedelta:
        return time_str

    # print(time_str)

    # Check for 'now'
    if time_str == "now":
        return datetime.now()

    # Check for a delta
    delta_re = re.compile(r"([+-]?)(\d*)([y|m|w|d|h|m|s])")
    match = delta_re.match(time_str)

    if match:

        dir = match.groups()[0]
        val = match.groups()[1]
        unit = match.groups()[2]

        if unit == "s":
            seconds = int(val)
        elif unit == "m":
            seconds = int(val) * 60
        elif unit == "h":
            seconds = int(val) * 60 * 60
        elif unit == "d":
            seconds = int(val) * 60 * 60 * 24
        elif unit == "w":
            seconds = int(val) * 60 * 60 * 24 * 7
        elif unit == "m":
            seconds = int(val) * 60 * 60 * 24 * 30
        elif unit == "y":
            seconds = int(val) * 60 * 60 * 24 * 365
        else:
            raise ValueError

        if dir == "-":
            seconds = seconds * -1

        return timedelta(seconds=seconds)

    # Check for a parsable time - this handles DICOM format fine
    time = dtparser.parse(time_str)
    if type(time) == datetime:
        return time

    raise ValueError("Can not parse time: {}".format(time_str))


@attr.s
class DatetimeInterval(object):

    start = attr.ib( type=datetime,  converter=parse_timestr )
    incr = attr.ib(  type=timedelta, converter=parse_timestr, default=None )
    end = attr.ib(   type=datetime,  converter=parse_timestr, default=None )  # Need either end or incr

    @start.default
    def set_now(self):
        return datetime.now()

    @start.validator
    def is_datetime(self, attrib, value):
        if type( value ) != datetime:
            raise ValueError("start must be of type datetime")

    def __attrs_post_init__(self):

        if type( self.end ) == datetime:
            self.incr = self.end - self.start
        elif type( self.incr ) == timedelta:
            self.end = self.start + self.incr
        else:
            raise ValueError("either end must be of type datetime or incr must be of type timedelta")

    def next(self):
        self.start = self.step()

    def step(self, safe=False):

        result = self.start + self.incr

        if result.date() != self.start.date():
            if self.incr < timedelta(seconds=0):
                result = datetime(self.start.year, self.start.month, self.start.day)
                if not safe:
                    result -= timedelta(seconds=1)
            else:
                result = datetime( result.year, result.month, result.day) - timedelta(seconds=1)
                if not safe:
                    result += timedelta(seconds=1)

        return result

    @property
    def earliest(self):

        if self.incr < timedelta(seconds=0):
            return self.step(safe=True)
        else:
            return self.start

    @property
    def latest(self):

        if self.incr > timedelta(seconds=0):
            return self.step(safe=True)
        else:
            return self.start

    def as_dicom(self):
        return dicom_strftime(self.earliest), dicom_strftime(self.latest)

    def as_dicom2(self):
        return dicom_strftime2(self.earliest), dicom_strftime2(self.latest)

    def __str__(self):
        str = "time interval: ({}, {})".format(self.earliest, self.latest)
        return str


def test_timerange():

    TR = DatetimeInterval("now", "+4h")
    print(TR)

    TR = DatetimeInterval("June 2, 2017", end="June 14, 2019")
    print(TR)

    TR = DatetimeInterval(incr="-3h")
    print(TR)

    print(TR.as_dicom())

    TR = DatetimeInterval("20180603120000", "+3h")
    print(TR)

    TR = DatetimeInterval("12pm", incr="-4h")

    for i in range(5):
        TR.next()
        print(TR)

    TR = DatetimeInterval("now", end="5pm")
    print(TR)
    TR.next()
    print(TR)
    W = DatetimeInterval(incr="1h")

    for i in range(15):
        W.next()
        print(W.as_dicom2())


logger = logging.getLogger(__name__)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_timerange()

