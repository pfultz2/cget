import six, inspect

def unspecified(obj, _type_):
    return True, ""

def default_checker(obj, _type_):
    return isinstance(obj, _type_), "type '{}'".format(_type_.__name__)

def get_checker(_type_):
    if inspect.isclass(_type_): return default_checker
    if six.callable(_type_): return _type_

def require_type(obj, _type_, name=None):
    b, msg = get_checker(_type_)(obj, _type_)
    if not b:
        s = 'Return'
        if name is not None: s = "Parameter '{0}'".format(name)
        raise TypeError("{0} should be {1} but found type '{2}' instead".format(s, b, type(obj)))

def check(_return_=unspecified, **_params_):
    def check_types(f, _params_ = _params_):
        @six.wraps(f)
        def m(*args, **kw):
            arg_names = six.get_function_code(f).co_varnames
            kw.update(zip(arg_names, args))
            for name, _type_ in six.iteritems(_params_):
                param = kw[name]
                require_type(param, _type_, name)
            r = f(**kw)
            require_type(r, _return_)
            return r
        return m
    return check_types
