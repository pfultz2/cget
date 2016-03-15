import six, inspect, os

def decorator_with_args(decorator):
    def f(*args, **kwargs):
        def g(func):
            return decorator(func, *args, **kwargs)
        return g
    return f

def identity_decorator(f):
    return f

def is_iterable(obj):
    return hasattr(obj, '__iter__')

def default_checker(obj, _type_):
    return isinstance(obj, _type_), "type '{}'".format(_type_.__name__)

def callable_checker(obj, f):
    return f(obj), f.__name__

def any_checkers(checkers):
    return any(map(lambda e:e[0], checkers))

def format_checkers(checkers):
    failed_checkers = filter(lambda e:not e[0], checkers)
    s_checkers = list(map(lambda e:e[1], failed_checkers))
    return "({})".format(','.join(s_checkers))

def get_checker(x):
    if inspect.isclass(x): return default_checker
    if six.callable(x): return callable_checker
    if is_iterable(x):
        def checker(obj, _type_):
            checkers = map(lambda e:get_checker(e)(obj, e), _type_)
            return any_checkers(checkers), format_checkers(checkers)
        return checker

def require_type(obj, _type_, fname, name=None):
    b, msg = get_checker(_type_)(obj, _type_)
    if not b:
        s = 'Return'
        if name is not None: s = "Parameter '{0}'".format(name)
        raise TypeError("{0} should be {1} but found type '{2}' instead for {3}".format(s, msg, type(obj), fname))
    return obj

DEBUG='DEBUG' in os.environ and len(os.environ['DEBUG']) > 0

if DEBUG:
    @decorator_with_args
    def params(f, **argument_types):
        @six.wraps(f)
        def check_call(*args, **kwargs):
            callargs = inspect.getcallargs(f, *args, **kwargs)
            for name, _type_ in six.iteritems(argument_types):
                require_type(callargs[name], _type_, f.__name__, name)
            return f(*args, **kwargs)
        return check_call

    @decorator_with_args
    def returns(f, _type_):
        @six.wraps(f)
        def check_call(*args, **kwargs):
            return require_type(f(*args, **kwargs), _type_, f.__name__)
        return check_call

else:
    def params(*arg, **kwargs):
        return identity_decorator
    def returns(*arg, **kwargs):
        return identity_decorator
