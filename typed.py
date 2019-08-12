#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import inspect
import re
from typing import *

__all__ = [
    # Functions
    "is_instance",
    # Decorators
    "checked",
    "type_checked",
    # Types
    "Matches",
]


def _cached(func):
    """
    Internal wrapper caching __getitem__ of generic types with a fallback to
    original function for non-hashable arguments.
    """
    cached = functools.lru_cache()(func)

    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return cached(*args, **kwargs)
        except TypeError:
            pass
        return func(*args, **kwargs)

    return inner


class _Matches:
    def __init__(self):
        self.__pattern__ = None
        self.__origin__ = None
        self.__name__ = "Matches"

    @_cached
    def __getitem__(self, item):
        if not isinstance(item, (str, bytes)):
            raise TypeError("{0} must be used as {0}[AnyStr]".format(self.__name__))
        obj = self.__class__()
        obj.__pattern__ = re.compile(item)
        return obj

    def __instancecheck__(self, instance):
        if self.__pattern__ is None:
            return False
        try:
            return self.__pattern__.match(instance) is not None
        except TypeError:
            return False

    def __repr__(self):
        if self.__pattern__:
            return "{}[{}]".format(self.__name__, repr(self.__pattern__.pattern))
        return self.__name__

    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate " + self.__name__)


Matches = _Matches()


def is_instance(obj, obj_type):
    """
    Return whether an object is an instance of a class or of a subclass thereof.
    A tuple, as in ``is_instance(x, (A, B, ...))``, may be given as the target to
    check against. This is equivalent to ``is_instance(x, A) or is_instance(x, B)
    or ...`` etc.
    """
    if isinstance(obj_type, tuple):
        for t in obj_type:
            if is_instance(obj, t):
                return True
        return False

    if obj_type.__class__ is type:
        return isinstance(obj, obj_type)
    elif obj_type is Optional or obj_type is Any:
        return True

    origin = getattr(obj_type, "__origin__")
    if origin is None:
        return isinstance(obj, obj_type)

    args = getattr(obj_type, "__args__")

    if origin is List:
        return isinstance(obj, origin) and all([is_instance(elem, args[0]) for elem in obj])
    elif origin is Union:
        return is_instance(obj, args)
    elif origin is Dict:
        return isinstance(obj, origin) and all(
            [is_instance(k, args[0]) and is_instance(v, args[1]) for k, v in obj.items()])
    elif origin is Tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return isinstance(obj, origin) and all([is_instance(elem, args[0]) for elem in obj])
        else:
            return isinstance(obj, origin) and len(args) == len(obj) and all(
                [is_instance(obj[i], args[i]) for i in range(len(args))])
    if origin is Callable:
        if not isinstance(obj, origin):
            return False

        input_args = args[0:-1]
        return_type = args[-1]
        spec = inspect.getfullargspec(obj)
        annotations = get_type_hints(obj if inspect.isfunction(obj) or inspect.ismethod(obj) else obj.__call__)

        if input_args[0] is Ellipsis:
            check_input = spec.varargs is not None
        else:
            start = 0 if inspect.isfunction(obj) else 1
            check_input = len(spec.args) - start == len(input_args)
            if check_input:
                for index, arg in enumerate(input_args, start):
                    if spec.args[index] not in annotations or annotations[spec.args[index]] is not arg:
                        check_input = False
                        break

        try:
            check_return = annotations["return"] is return_type
        except KeyError:
            check_return = True
        return check_input and check_return
    else:
        raise NotImplementedError(str(origin) + " with args " + str(args) + " is not supported")


def _object_type(obj_type):
    obj_type_str = repr(obj_type)
    return obj_type_str[7:] if obj_type_str.startswith("typing.") else obj_type.__name__


def _build_wrapper(function, _is_instance):
    annotations = get_type_hints(function)
    if not annotations:
        return function

    spec = inspect.getfullargspec(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        for index, arg in enumerate(args):
            try:
                if index < len(spec.args):
                    obj_type = annotations[spec.args[index]]
                else:
                    obj_type = annotations[spec.varargs]
            except KeyError:
                continue

            if not _is_instance(arg, obj_type):
                raise ValueError("Expecting {} for arg {}. Got {}.".format(
                    _object_type(obj_type), index + 1, arg.__class__.__name__))

        for name, arg in kwargs.items():
            try:
                if name in spec.kwonlyargs:
                    obj_type = annotations[name]
                else:
                    obj_type = annotations[spec.varkw]
            except KeyError:
                continue

            if not _is_instance(arg, obj_type):
                raise ValueError("Expecting {} for kwarg {}. Got {}.".format(
                    _object_type(obj_type), name, arg.__class__.__name__))

        return function(*args, **kwargs)

    wrapper.__signature__ = inspect.signature(function)
    return wrapper


def _checked(obj, _is_instance):
    if inspect.isfunction(obj):
        return _build_wrapper(obj, _is_instance)
    elif isinstance(obj, (staticmethod, classmethod)):
        return obj.__class__(_build_wrapper(obj.__func__, _is_instance))

    # Assuming its a class
    for name, method in obj.__dict__.items():
        if isinstance(method, (staticmethod, classmethod)):
            setattr(obj, name, method.__class__(_build_wrapper(method.__func__, _is_instance)))
        elif inspect.isfunction(method):
            setattr(obj, name, _build_wrapper(method, _is_instance))

    return obj


def checked(function):
    """
    Decorates **function** so all the arguments with type hints are
    validated against them using the custom is_instance function.
    The decorated function raises ValueError if the validation fails.
    """
    return _checked(function, is_instance)


def type_checked(function):
    """
    Decorates **function** so all the arguments with type hints are
    validated against them using the builtin isinstance function.
    The decorated function raises ValueError if the validation fails.
    """
    return _checked(function, isinstance)