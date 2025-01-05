#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import inspect
import json
import threading
import types
import typing
from typing import NamedTuple, Callable, List, Tuple, Type, TypeVar, Optional, Union, \
    get_origin, get_args, get_type_hints

try:
    from collections.abc import Hashable
except ImportError:
    from typing import Hashable

__all__ = [
    # Functions
    "is_instance", "is_type", "is_type_var", "type_repr",
    "is_nullable", "validate_attribute_type", "validate_attribute",
    # Decorators
    "checked", "type_checked",
    # Classes
    "DataStruct", "JSONStruct",
]

T = TypeVar("T")

DefaultValue = NamedTuple("DefaultValue", (("has_value", bool), ("value", any)))
Params = NamedTuple("Params", (("from_converter", Optional[Callable]), ("default", DefaultValue)))


def is_nullable(attribute_type):
    return attribute_type is type(None) or (
            get_origin(attribute_type) is Union and type(None) in get_args(attribute_type))


def validate_attribute_type(attribute, attribute_type):
    origin = get_origin(attribute_type)
    if origin in (Union, tuple):
        for arg in get_args(attribute_type):
            validate_attribute_type(attribute, arg)
    elif origin is list:
        args = get_args(attribute_type)
        if args:
            l_type, = args
            validate_attribute_type(attribute, l_type)
    elif origin is dict:
        args = get_args(attribute_type)
        if args:
            k_type, v_type = args
            validate_attribute_type(attribute, k_type)
            if not issubclass(get_origin(k_type) or k_type, Hashable):
                raise TypeError("Map keys must be hashable")
            validate_attribute_type(attribute, v_type)
    elif type(attribute_type) is not type:
        raise TypeError("Invalid type provided {} for attribute {}".format(attribute_type, attribute))


def validate_attribute(struct, attribute, attribute_type, value):
    AttributeValidator(struct).handle(attribute, attribute_type, value)


class DataStruct(object):
    _SPEC_FIELD = "_spec"

    @classmethod
    def attributes(cls) -> List[Tuple[str, type, Params]]:
        return [attr for attr in (
            getattr(value.fset, cls._SPEC_FIELD, None)
            for clazz in cls.__mro__
            for value in clazz.__dict__.values()
            if isinstance(value, property) and value.fget is not None and value.fset is not None
        ) if attr is not None]

    @classmethod
    def from_dict(cls, data, strict=False):
        if strict:
            difference = set(data).difference({attribute for attribute, _, _ in cls.attributes()})
            if difference:
                raise ValueError("Data contains unexpected attributes for {}: {}".format(
                    cls.__name__, ", ".join(map(repr, difference))))

        obj = cls()
        default_converter = ConverterFrom(cls.__name__)

        for attribute, attribute_type, params in cls.attributes():
            # We can use obj as sentinel as well
            value = data.get(attribute, obj)
            if value is not obj:
                if params.from_converter and not (attribute_type and is_nullable(attribute_type) and value is None):
                    try:
                        value = params.from_converter(value)
                    except ValueError as e:
                        raise ValueError("Failed to convert {} {}: {}".format(cls.__name__, attribute, e))

                if attribute_type:
                    value = default_converter.handle(attribute, attribute_type, value)
                obj.__setattr__(attribute, value)
            else:
                if params.default.has_value:
                    obj.__setattr__(attribute, params.default.value)
                else:
                    raise ValueError("No value for {} attribute {}".format(cls.__name__, attribute))

        return obj

    @classmethod
    def attr(cls, attribute: str, attribute_type: Type[T] = None, **kwargs) -> T:
        sentinel = object()
        default = kwargs.pop("default", sentinel)
        from_converter = kwargs.pop("from_converter", None)
        if kwargs:
            raise TypeError("Unexpected arguments provided: {}".format(", ".join(kwargs)))

        if attribute_type:
            validate_attribute_type(attribute, attribute_type)
            if default is None and not is_nullable(attribute_type):
                attribute_type = Optional[attribute_type]

            def setter(self, value):
                validate_attribute(self.__class__.__name__, attribute, attribute_type, value)
                self.__dict__[attribute] = value
        else:
            def setter(self, value):
                self.__dict__[attribute] = value

        def getter(self):
            return self.__dict__.get(attribute)

        spec = (attribute, attribute_type, Params(
            from_converter,
            DefaultValue(False, None) if default is sentinel else DefaultValue(True, default)))
        setattr(setter, cls._SPEC_FIELD, spec)
        return property(getter, setter)

    def to_dict(self):
        default_converter = ConverterTo(self.__class__.__name__)
        return {attribute: default_converter.handle(attribute, attribute_type, self.__dict__.get(attribute))
                for attribute, attribute_type, _ in self.attributes()}

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError("No such attribute '{}'".format(k))
            self.__setattr__(k, v)

    def __repr__(self):
        return str(self.to_dict())


class JSONStruct(DataStruct):
    @classmethod
    def load(cls, fp):
        return cls.from_dict(json.load(fp))

    @classmethod
    def loads(cls, s):
        return cls.from_dict(json.loads(s))

    def dump(self, fp, **kwargs):
        return json.dump(self.to_dict(), fp, **kwargs)

    def dumps(self, **kwargs):
        return json.dumps(self.to_dict(), **kwargs)


class AttributeTypeHandler(object):
    _handle_exception_type = ValueError
    _size_exception_type = ValueError

    def __init__(self, name):
        self._name = name

    def handle(self, attribute, attribute_type, value):
        origin = get_origin(attribute_type)
        if origin is Union:
            value = self._handle_union(attribute, attribute_type, value)
        elif origin is tuple:
            value = self._handle_tuple(attribute, attribute_type, value)
        elif origin is list:
            value = self._handle_list(attribute, attribute_type, value)
        elif origin is dict:
            value = self._handle_dict(attribute, attribute_type, value)
        else:
            value = self._handle_extra(attribute, attribute_type, value)
        return value

    def _handle_union(self, attribute, attribute_type, value):
        for arg in get_args(attribute_type):
            try:
                return self.handle(attribute, arg, value)
            except (self._handle_exception_type, self._size_exception_type):
                pass
        self._fail_handle(attribute, attribute_type, value)

    def _handle_tuple(self, attribute, attribute_type, value):
        self._validate_instance(attribute, tuple, value)
        args = get_args(attribute_type)
        if args:
            if args[-1] is Ellipsis:
                t_type, _ = args
                value = self._handle_inner(tuple, (
                    self.handle(attribute + "[" + str(i) + "]", t_type, v)
                    for i, v in enumerate(value)))
            elif args == ((),):
                self._validate_size(attribute, 0, len(value))
            else:
                self._validate_size(attribute, len(args), len(value))
                value = self._handle_inner(tuple, (
                    self.handle(attribute + "[" + str(i) + "]", args[i], v)
                    for i, v in enumerate(value)))
        return value

    def _handle_list(self, attribute, attribute_type, value):
        self._validate_instance(attribute, list, value)
        args = get_args(attribute_type)
        if args and value:
            l_type, = args
            value = self._handle_inner(list, (self.handle(attribute + "[...]", l_type, v) for v in value))
        return value

    def _handle_dict(self, attribute, attribute_type, value):
        self._validate_instance(attribute, dict, value)
        args = get_args(attribute_type)
        if args and value:
            k_type, v_type = args
            value = self._handle_inner(dict, (
                (self.handle(attribute + ".<k>", k_type, k), self.handle(attribute + ".<k, v>", v_type, v))
                for k, v in value.items()))
        return value

    def _handle_extra(self, attribute, attribute_type, value):
        raise NotImplemented("_handle_extra method must be implemented by subclasses")

    def _handle_inner(self, parent_type, inner_values):
        raise NotImplemented("_handle_inner method must be implemented by subclasses")

    def _validate_instance(self, attribute, attribute_type, value):
        if not isinstance(value, attribute_type):
            self._fail_handle(attribute, attribute_type, value)

    def _fail_handle(self, attribute, expected_type, actual_value):
        raise self._handle_exception_type(
            "Unexpected value type for {} attribute '{}'. Expecting {} but actual type is {}".format(
                self._name, attribute, expected_type, actual_value.__class__))

    def _validate_size(self, attribute, expected_size, actual_size):
        if expected_size != actual_size:
            raise self._size_exception_type(
                "Unexpected size for {} attribute '{}. Expecting {} but actual size is {}".format(
                    self._name, attribute, expected_size, actual_size))


class AttributeValidator(AttributeTypeHandler):
    _handle_exception_type = TypeError
    _size_exception_type = TypeError

    def _handle_extra(self, attribute, attribute_type, value):
        if not isinstance(value, attribute_type):
            self._fail_handle(attribute, attribute_type, value)

    def _handle_inner(self, parent_type, inner_values):
        for _ in inner_values:
            pass


class Converter(AttributeTypeHandler):
    _struct_type = type(None)

    def _handle_extra(self, attribute, attribute_type, value):
        if isinstance(attribute_type, type) and issubclass(attribute_type, self._struct_type):
            value = self._convert_data_struct(attribute_type, value)
        elif not isinstance(value, attribute_type):
            self._fail_handle(attribute, attribute_type, value)
        return value

    def _handle_inner(self, parent_type, inner_values):
        return parent_type(inner_values)

    def _convert_data_struct(self, attribute_type, value):
        raise NotImplemented("Method must be implemented by subclasses")


class ConverterFrom(Converter):
    _handle_exception_type = ValueError
    _size_exception_type = ValueError
    _struct_type = DataStruct

    def _convert_data_struct(self, attribute_type, value):
        return attribute_type.from_dict(value) if isinstance(value, dict) else value


class ConverterTo(Converter):
    _handle_exception_type = RuntimeError
    _size_exception_type = RuntimeError
    _struct_type = DataStruct

    def _convert_data_struct(self, attribute_type, value):
        return value.to_dict()


def type_repr(obj):
    """
    Returns a string representation of the provided **obj** object.
    :rtype: str
    """
    if isinstance(obj, list):
        representation = _type_repr_dynamic_inner_types("List", obj)
    elif isinstance(obj, set):
        representation = _type_repr_dynamic_inner_types("Set", obj)
    elif isinstance(obj, frozenset):
        representation = _type_repr_dynamic_inner_types("FrozenSet", obj)
    elif isinstance(obj, tuple):
        representation = _type_repr_fixed_inner_types("Tuple", obj)
    elif isinstance(obj, dict):
        representation = _type_repr_dict(obj)
    elif inspect.isfunction(obj):
        representation = _type_repr_callable(obj, is_method=False)
    elif inspect.ismethod(obj):
        representation = _type_repr_callable(obj, is_method=True)
    elif isinstance(obj, type):
        representation = "Type[" + obj.__name__ + "]"
    else:
        representation = obj.__class__.__name__

    return representation


def _type_repr_dynamic_inner_types(parent_repr, obj):
    representation = parent_repr
    inner = {type_repr(item) for item in obj}
    if len(inner) == 1:
        representation += "[" + inner.pop() + "]"
    elif len(inner) > 1:
        representation += "[Union[" + ", ".join(sorted(inner)) + "]]"
    return representation


def _type_repr_fixed_inner_types(parent_repr, obj):
    representation = parent_repr
    inner = [type_repr(item) for item in obj]
    if len(inner) == 0:
        representation += "[()]"
    elif len(inner) == 1:
        representation += "[" + inner[0] + "]"
    elif all(i == inner[0] for i in inner):
        representation += "[" + inner[0] + ", ...]"
    else:
        representation += "[" + ", ".join(inner) + "]"
    return representation


def _type_repr_dict(obj):
    representation = "Dict"
    if obj:
        keys = {type_repr(k) for k in obj.keys()}
        values = {type_repr(v) for v in obj.values()}
        keys_repr = keys.pop() if len(keys) == 1 else "Union[" + ", ".join(sorted(keys)) + "]"
        values_repr = values.pop() if len(values) == 1 else "Union[" + ", ".join(sorted(values)) + "]"
        representation += "[" + keys_repr + ", " + values_repr + "]"
    return representation


def _type_repr_callable(obj, is_method=False):
    representation = "Callable"
    spec = inspect.getfullargspec(obj)
    annotations = get_type_hints(obj)
    args = spec.args[1 if is_method else 0:]

    if spec.varargs or spec.varkw:
        input_args = "..."
    elif args:
        input_annotations = (
            "Any" if annotation is None else _type_hint_repr(annotation)
            for annotation in (annotations.get(arg) for arg in args))
        input_args = "[" + ", ".join(input_annotations) + "]"
    else:
        input_args = "[]"

    return_annotation = annotations.get("return")
    output_args = "Any" if return_annotation is None else _type_hint_repr(return_annotation)
    representation += "[" + input_args + ", " + output_args + "]"
    return representation


def _type_hint_repr(obj_type):
    if isinstance(obj_type, type):
        type_hint_repr = obj_type.__name__
    else:
        origin = get_origin(obj_type)
        if origin:
            args = get_args(obj_type)
            if origin is Union and type(None) in args:
                origin_name = "Optional"
                args = (a for a in args if a is not type(None))
            else:
                origin_name = getattr(obj_type, "_name", None) or _type_hint_repr(origin)
            type_hint_repr = origin_name + "[" + ", ".join(_type_hint_repr(a) for a in args) + "]"
        else:
            type_hint_repr = getattr(obj_type, "_name", None) or repr(obj_type)
    return type_hint_repr


def is_instance(obj, obj_type):
    """
    Return whether an object is an instance of a class or of a subclass thereof.
    A tuple, as in ``is_instance(x, (A, B, ...))``, may be given as the target to
    check against. This is equivalent to ``is_instance(x, A) or is_instance(x, B)
    or ...`` etc.
    :rtype: bool
    """
    if isinstance(obj_type, tuple):
        return any(is_instance(obj, t) for t in obj_type)

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
                        _type_hint_repr(obj_type), index + 1, type_repr(arg)))

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
                        _type_hint_repr(obj_type), name, type_repr(arg)))

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
        ret = any(p in child_type.__mro__ for p in parent_type)
    elif contravariant:
        ret = any(child_type in p.__mro__ for p in parent_type)
    else:
        ret = child_type in parent_type
    return ret


def is_type_var(child_type, type_var):
    constraints = [type_var.__bound__] if type_var.__bound__ else type_var.__constraints__
    return is_type(child_type, *constraints, covariant=type_var.__covariant__,
                   contravariant=type_var.__contravariant__) if constraints else True


def _check_generics_parameters(args, cls):
    parameters = _get_parameters(cls)
    for i, parameter in enumerate(parameters):
        if not is_type_var(args[i], parameter):
            raise TypeError("Generic '{}' does not accept {} constraint".format(
                cls.__name__, _type_hint_repr(args[i])))


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
