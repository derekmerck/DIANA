import logging
from datetime import datetime, timedelta
import attr

@attr.s
class DatetimeInterval(object):
    begin = attr.ib( type=datetime )
    end = attr.ib( type=datetime, default=None )
    incr = attr.ib( type=timedelta, default=None )

    def __attrs_post_init__(self):
        if type( self.end ) == datetime:
            self.incr = self.end - self.begin

        elif type( self.incr ) == timedelta:
            self.end = self.begin + self.incr

        else:
            raise ValueError("Either 'end' must be of type datetime or incr must be of type 'timedelta'")

    @property
    def latest(self):
        if self.begin > self.end:
            return self.begin
        return self.end

    @property
    def earliest(self):
        if self.begin > self.end:
            return self.begin
        return self.end

    def __next__(self):
        stride = self.incr
        self.begin = self.end
        self.end = self.end + self.incr


def test_dtinterval():

    d = datetime( year=2020, month=1, day=20, hour=12 )
    e = datetime( year=2020, month=1, day=20, hour=12, minute=30 )

    a = DatetimeInterval( begin=d, incr=e-d )
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