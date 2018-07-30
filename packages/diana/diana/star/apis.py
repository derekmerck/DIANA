import logging, sys
from typing import Callable
import attr
from ..apis import Orthanc, Redis, DicomFile, Splunk, Dixel
from .tasks import do


# Decorator
def star(func: Callable):
    def wrapper(self, *args, **kwargs):
        celery_args = {}
        if self.celery_queue:
            celery_args['queue'] = self.celery_queue
        if not kwargs:
            kwargs = {}
        kwargs['pattern'] = self.pattern
        kwargs['method'] = func.__name__
        # logging.warning("wrapper: {}".format(kwargs))
        return do.apply_async(args, kwargs, **celery_args)

    def sig(*args, **kwargs):
        return do.s(*args, method=func.__name__, **kwargs)

    # print(dir(func))
    # print(func.__module__)  # Here is the method, where is the caller?
    # print(sys._getframe(1).f_code.co_name )
    wrapper.s = sig

    return wrapper


@attr.s
class DistribMixin(object):
    celery_queue = attr.ib( default='default' )

    @star
    def get(self, item, **kwargs):
        pass

    @star
    def put(self, item, **kwargs):
        pass

    @star
    def handle(self, item, **kwargs):
        pass


@attr.s
class Orthanc(DistribMixin, Orthanc):
    pass


@attr.s
class Redis(DistribMixin, Redis):
    pass


@attr.s
class DicomFile(DistribMixin, DicomFile):
    celery_queue = attr.ib( default="file" )


@attr.s
class Splunk(DistribMixin, Splunk):
    pass