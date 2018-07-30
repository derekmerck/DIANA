import uuid, logging
import attr
import inspect
from pprint import pprint



@attr.s(cmp=False, hash=None)
class Pattern(object):
    uid = attr.ib(factory=uuid.uuid4)
    logger = attr.ib(init=False)

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def __hash__(self):
        return hash(self.uid)

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def pattern(self):
        pattern = {'class': self.__class__.__name__}
        for item in self.__init__.__code__.co_varnames[1:]:
            # Ignore celery meta-properties
            if item.startswith("celery"):
                continue
            pattern[item] = self.__dict__[item]
        # logging.warning("pattern: {}".format( pattern ))
        return pattern

    def get(self, *args, **kwargs):
        # print(self.__class__.__name__)
        raise NotImplementedError

    def put(self, *args, **kwargs):
        raise NotImplementedError

    def handle(self, *args, **kwargs):
        "Call a class-specific method"
        # print(self.__class__.__name__)
        # print(kwargs.get("method"))
        method = kwargs.get("method")
        func = self.__getattribute__(method)
        del(kwargs['method'])
        return func(*args, **kwargs)

    @staticmethod
    def factory(**pattern):
        """
        Patterned objects can be instanced from a dictionary through a factory function, but
        the target class _must_ be in the global namespace.  For example, in diana, the api
        factory imports all diana.apis.
        """

        class_name = pattern.get('class')
        del (pattern['class'])

        # pprint(inspect.stack()[1][0].f_globals)
        _cls = inspect.stack()[1][0].f_globals[class_name]

        # _cls = globals()[class_name]
        return _cls(**pattern)



