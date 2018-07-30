# Uses the apis.pattern_factory to convert calls to diana-star api objects into calls
# to locals diana api objects

import logging
from ..apis.factory import factory
from . import app


@app.task
def do(*args, **kwargs):
    pattern = kwargs.get("pattern")
    logging.debug('doing: {}'.format(pattern))
    handler = factory(**pattern)
    del(kwargs['pattern'])
    return handler.handle(*args, **kwargs)

    # method = kwargs.get("method")
    # func = cls.__getattribute__(method)
    # del (kwargs['method'])
    # return func(*args, **kwargs)


@app.task(name="message")
def message(msg: str, *args, **kwargs):
    print(msg)