#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import inspect
import re
import threading
import types
import typing

__all__ = [
    # Functions
    "is_instance", "is_type", "is_type_var", "type_repr",
    # Decorators
    "checked", "type_checked",
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


def _object_type(obj_type):
    obj_type_str = repr(obj_type)
    return (obj_type_str.replace("typing.", "") if "typing." in obj_type_str
            else getattr(obj_type, "__name__", obj_type_str))


def type_repr(obj):
    """
    Returns a string representation of the provided **obj** object.
    :rtype: str
    """
    if isinstance(obj, (list, set, frozenset)):
        if isinstance(obj, list):
            representation = "List"
        elif isinstance(obj, set):
            representation = "Set"
        else:
            representation = "FrozenSet"
        inner = {type_repr(item) for item in obj}
        if len(inner) == 1:
            representation += "[" + inner.pop() + "]"
        elif len(inner) > 1:
            representation += "[Union[" + ", ".join(sorted(inner)) + "]]"
    elif isinstance(obj, tuple):
        representation = "Tuple"
        inner = [type_repr(item) for item in obj]
        if len(inner) == 1:
            representation += "[" + inner[0] + "]"
        elif len(set(inner)) == 1:
            representation += "[" + inner[0] + ", ...]"
        elif len(inner) > 1:
            representation += "[" + ", ".join(sorted(inner)) + "]"
    elif isinstance(obj, dict):
        representation = "Dict"
        if len(obj):
            keys = {type_repr(k) for k in obj.keys()}
            values = {type_repr(v) for v in obj.values()}

            if len(keys) == 1:
                keys_repr = keys.pop()
            else:
                keys_repr = "Union[" + ", ".join(sorted(keys)) + "]"
            if len(values) == 1:
                values_repr = values.pop()
            else:
                values_repr = "Union[" + ", ".join(sorted(values)) + "]"
            representation += "[" + keys_repr + ", " + values_repr + "]"
    elif inspect.isfunction(obj) or inspect.ismethod(obj):
        representation = "Callable"
        spec = inspect.getfullargspec(obj)
        annotations = typing.get_type_hints(obj)
        args = spec.args[0 if inspect.isfunction(obj) else 1:]

        if args:
            input_annotations = []
            for arg in args:
                if arg in annotations:
                    input_annotations.append(_object_type(annotations[arg]))
                else:
                    input_annotations.append("Any")
            input_args = "[" + ", ".join(input_annotations) + "]"
        elif spec.varargs:
            input_args = "..."
        else:
            input_args = None

        if "return" in annotations:
            output_args = _object_type(annotations["return"])
        else:
            output_args = "Any"

        if input_args is not None and output_args is not None:
            representation += "[" + input_args + ", " + output_args + "]"
    elif isinstance(obj, type):
        representation = "Type[" + obj.__name__ + "]"
    else:
        representation = obj.__class__.__name__

    return representation


def is_instance(obj, obj_type):
    """
    Return whether an object is an instance of a class or of a subclass thereof.
    A tuple, as in ``is_instance(x, (A, B, ...))``, may be given as the target to
    check against. This is equivalent to ``is_instance(x, A) or is_instance(x, B)
    or ...`` etc.
    :rtype: bool
    """
    if isinstance(obj_type, tuple):
        for t in obj_type:
            if is_instance(obj, t):
                return True
        return False

    if obj_type.__class__ is type:
        return isinstance(obj, obj_type)
    elif obj_type is typing.Optional or obj_type is typing.Any:
        return True
    elif isinstance(obj_type, typing.TypeVar):
        return is_type_var(obj.__class__, obj_type)
    elif obj_type is typing.Generic:
        return is_type(obj.__class__, typing.Generic, covariant=True)

    origin = typing.get_origin(obj_type)
    if origin is None:
        return isinstance(obj, obj_type)

    args = typing.get_args(obj_type)
    if not args:
        return isinstance(obj, origin)

    if is_type(obj.__class__, typing.Generic, covariant=True):
        return (is_type(origin, typing.Generic, covariant=True) and
                len(args) == len(obj.__parameters__) and
                all([args[i] is p for i, p in enumerate(obj.__parameters__)]))

    name = repr(obj_type)[7:]

    if name.startswith("List") or name.startswith("Set") or name.startswith("FrozenSet"):
        return isinstance(obj, origin) and all([is_instance(elem, args[0]) for elem in obj])
    elif name.startswith("Union"):
        return is_instance(obj, args)
    elif name.startswith("Dict"):
        return isinstance(obj, origin) and all(
            [is_instance(k, args[0]) and is_instance(v, args[1]) for k, v in obj.items()])
    elif name.startswith("Tuple"):
        if len(args) == 2 and args[1] is Ellipsis:
            return isinstance(obj, origin) and all([is_instance(elem, args[0]) for elem in obj])
        else:
            return isinstance(obj, origin) and len(args) == len(obj) and all(
                [is_instance(obj[i], args[i]) for i in range(len(args))])
    elif name.startswith("Callable"):
        if not isinstance(obj, origin):
            return False

        input_args = args[0:-1]
        return_type = args[-1]
        spec = inspect.getfullargspec(obj)
        annotations = typing.get_type_hints(obj if inspect.isfunction(obj) or inspect.ismethod(obj) else obj.__call__)

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
    elif name.startswith("Type"):
        return isinstance(obj, origin) and is_type(obj, *args, covariant=True)
    else:
        raise NotImplementedError("{}: {} with args {} is not supported".format(repr(obj_type), str(origin), str(args)))


class _ObjHints:
    def __init__(self):
        self._count = 0
        self._data = {}
        self._lock = threading.RLock()

    def add(self, obj, hint):
        with self._lock:
            self._count += 1
            self._data[self._count] = (threading.get_ident(), obj, hint)
            return self._count

    def remove(self, identifier):
        with self._lock:
            del self._data[identifier]

    def get(self, obj):
        thread_id = threading.get_ident()
        with self._lock:
            for i in sorted(self._data, reverse=True):
                t, o, h = self._data[i]
                if t == thread_id and o is obj:
                    return h
        return None


_hints = _ObjHints()


def _get_parameters(obj):
    if obj.__parameters__:
        return obj.__parameters__
    if obj.__origin__:
        return _get_parameters(obj.__origin__)
    return ()


def _get_type_of_type_var(arg, obj_type, type_vars):
    if isinstance(obj_type, typing.TypeVar):
        if obj_type in type_vars:
            obj_type = type_vars[obj_type]
        else:
            type_vars[obj_type] = type(arg)
    return obj_type


def _has_function(obj, function):
    return function in obj.__class__.__dict__.values()


def _build_wrapper(function, _is_instance):
    annotations = typing.get_type_hints(function)
    if not annotations:
        return function

    spec = inspect.getfullargspec(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        type_vars = {}
        saved_hints = []

        try:
            if (len(args) > 0 and is_type(args[0].__class__, typing.Generic, covariant=True)
                    and _has_function(args[0], wrapper)):
                if hasattr(args[0], "__orig_class__"):
                    clazz = args[0].__orig_class__
                else:
                    clazz = _hints.get(args[0])
                if clazz is not None:
                    type_vars = {k: clazz.__args__[i] for i, k in enumerate(_get_parameters(clazz))}

            for index, arg in enumerate(args):
                try:
                    if index < len(spec.args):
                        obj_type = annotations[spec.args[index]]
                    else:
                        obj_type = annotations[spec.varargs]
                except KeyError:
                    continue

                obj_type = _get_type_of_type_var(arg, obj_type, type_vars)

                if not _is_instance(arg, obj_type):
                    raise TypeError("Expecting {} for arg {}. Got {}.".format(
                        _object_type(obj_type), index + 1, type_repr(arg)))

                if (is_type(arg.__class__, typing.Generic, covariant=True) and not hasattr(arg, "__orig_class__") and
                        hasattr(obj_type, "__parameters__")):
                    saved_hints.append(_hints.add(arg, obj_type))

            for name, arg in kwargs.items():
                try:
                    if name in spec.kwonlyargs:
                        obj_type = annotations[name]
                    else:
                        obj_type = annotations[spec.varkw]
                except KeyError:
                    continue

                obj_type = _get_type_of_type_var(arg, obj_type, type_vars)

                if not _is_instance(arg, obj_type):
                    raise TypeError("Expecting {} for kwarg {}. Got {}.".format(
                        _object_type(obj_type), name, type_repr(arg)))

                if (is_type(arg.__class__, typing.Generic, covariant=True) and not hasattr(arg, "__orig_class__") and
                        hasattr(obj_type, "__parameters__")):
                    saved_hints.append(_hints.add(arg, obj_type))

            return function(*args, **kwargs)
        finally:
            for hint in saved_hints:
                _hints.remove(hint)

    wrapper.__signature__ = inspect.signature(function)
    return wrapper


def is_type(child_type, *parent_type, covariant=False, contravariant=False):
    # TODO: Also use __orig_bases__
    if covariant:
        for p in parent_type:
            if p in child_type.__mro__:
                return True
    elif contravariant:
        for p in parent_type:
            if child_type in p.__mro__:
                return True
    else:
        return child_type in parent_type

    return False


def is_type_var(child_type, type_var):
    constraints = [type_var.__bound__] if type_var.__bound__ else type_var.__constraints__
    return is_type(child_type, *constraints, covariant=type_var.__covariant__,
                   contravariant=type_var.__contravariant__) if constraints else True


def _check_generics_parameters(args, cls):
    parameters = _get_parameters(cls)
    for i, parameter in enumerate(parameters):
        if not is_type_var(args[i], parameter):
            raise TypeError("Generic '{}' does not accept {} constraint".format(
                cls.__name__, _object_type(args[i])))


def _wrap_generic(obj):
    if hasattr(obj, "__class_getitem__"):
        default_class_getitem = obj.__class_getitem__.__func__

        @functools.wraps(default_class_getitem)
        def __class_getitem__(cls, items):
            if not isinstance(items, tuple):
                items = (items,)

            result = default_class_getitem(cls, items)
            _check_generics_parameters(items, cls)
            return result

        __class_getitem__.__signature__ = inspect.signature(default_class_getitem)
        obj.__class_getitem__ = types.MethodType(__class_getitem__, obj)
    else:
        default_new = obj.__new__

        @functools.wraps(default_new)
        def __new__(cls, *args, **kwargs):
            if getattr(cls, "__args__", False):
                _check_generics_parameters(cls.__args__, cls)
            return default_new(cls, *args, **kwargs)

        __new__.__signature__ = inspect.signature(default_new)
        obj.__new__ = __new__


def _checked(obj, _is_instance, raises=True):
    if inspect.isfunction(obj):
        return _build_wrapper(obj, _is_instance)
    elif isinstance(obj, (staticmethod, classmethod)):
        return obj.__class__(_build_wrapper(obj.__func__, _is_instance))
    elif isinstance(obj, type):
        for name, method in obj.__dict__.items():
            if name not in ("_gorg", "__next_in_mro__", "__origin__"):
                wrapped_method = _checked(method, _is_instance, raises=False)
                if wrapped_method is not None:
                    setattr(obj, name, wrapped_method)
        if is_type(obj, typing.Generic, covariant=True):
            _wrap_generic(obj)
        return obj
    elif raises:
        raise TypeError("decorator must be applied to either functions or classes")
    return None


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
