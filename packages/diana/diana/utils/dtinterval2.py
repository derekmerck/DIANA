import logging
from typing import Union
from datetime import datetime, timedelta
import attr


def convert_timedelta(value):
    if isinstance(value, timedelta):
        return datetime.now() + value
    return value


@attr.s
class DatetimeInterval(object):
    # begin: Union[datetime, timedelta, None] = attr.ib(convert=convert_timedelta)
    # end: Union[datetime, timedelta, None] = attr.ib(convert=convert_timedelta)

    begin = attr.ib(convert=convert_timedelta)
    end = attr.ib(convert=convert_timedelta)

    @begin.default
    @end.default
    def set_now(self) -> datetime:
        return datetime.now()

    @property
    def earliest(self) -> datetime:
        if self.begin <= self.end:
            return self.begin
        else:
            return self.end

    @property
    def latest(self) -> datetime:
        if self.begin <= self.end:
            return self.end
        else:
            return self.begin

    @property
    def incr(self) -> timedelta:
        return self.end - self.begin

    def __next__(self):
        incr = self.incr
        self.begin = self.end
        self.end = self.end + incr


def test_dtinterval():

    d = datetime( year=2020, month=1, day=20, hour=12 )
    e = datetime( year=2020, month=1, day=20, hour=12, minute=30 )

    a = DatetimeInterval( begin=d, end=e )
    next(a)
    next(a)
    assert( a.end == datetime(2020, 1, 20, 13, 30) )

    a = DatetimeInterval( begin=e, end=d )
    next(a)
    next(a)
    assert( a.end == datetime(2020, 1, 20, 11, 00) )


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_dtinterval()