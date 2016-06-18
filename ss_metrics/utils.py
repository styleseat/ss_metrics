from __future__ import absolute_import

import inspect


def get_function_name(fn):
    """Get the fully qualified name of a function.

    This function accounts for module-level functions and instance methods.
    """
    module = inspect.getmodule(fn)
    if module is None:
        raise ValueError(
            'Could not resolve module for function {name}'.format(
                name=fn.__name__))
    module_name = module.__name__
    if inspect.isfunction(fn):
        try:
            # Unbound python3 method
            qualname = fn.__qualname__
        except AttributeError:
            qualname = fn.__name__
    elif inspect.ismethod(fn):
        instance = fn.__self__
        if instance is None:
            # Unbound python2 method
            qualname = '.'.join((fn.im_class.__name__, fn.__name__))
        else:
            # Bound method
            cls = instance if inspect.isclass(instance) else type(instance)
            qualname = '.'.join((cls.__name__, fn.__name__))
    else:
        raise ValueError(
            'Could not resolve qualified name for function {name}'.format(
                name=fn.__name__))
    return '.'.join((module_name, qualname))
