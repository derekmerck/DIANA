from diana.utils import Pattern


class partial(object):

    def __init__(self, func=None, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, item):
        return self.func(item, *self.args, **self.kwargs)


class bpartial(partial):
    # bound partial

    def __init__(self, func=None, *args, **kwargs):
        self.obj = func.__self__
        self.func_name = func.__name__
        super(bpartial, self).__init__(None, *args, **kwargs)

    def __call__(self, item):
        func = getattr(self.obj, self.func_name)
        return func( item, *self.args, **self.kwargs )


class ppartial(partial):
    # serializable bound partial using Pattern

    def __init__(self, func=None, *args, **kwargs):
        obj = func.__self__
        self.pattern = obj.pattern
        self.func_name = func.__name__
        super(ppartial, self).__init__(None, *args, **kwargs)

    def __call__(self, item):
        obj = Pattern.factory(**self.pattern)
        func = getattr(obj, self.func_name)
        return func( item, *self.args, **self.kwargs )



class chain(object):

    def __init__(self, *args):
        self.partials = args

    def __call__(self, item):
        for p in self.partials:
            item = p(item)


class G(Pattern):

    def g( self, item:int, *args, **kwargs) -> int:
        return f(item, args, kwargs)

def f( item:str, *args, **kwargs ) -> str:
    print(item)
    print(args)
    print(kwargs)
    return item + "X"


p = partial(f)
q = partial(f, x="cat", y="dog")
r = partial(f, "apple", "orange", x="bird")

s = chain( p, q, r )

p("partial")
s("chain")

obj = G()

a = ppartial( obj.g )
b = ppartial( obj.g, x="cat" )
c = chain( a, b )

a("ppartial")
c("pchain")

