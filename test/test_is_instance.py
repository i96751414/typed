#!/usr/bin/env python
# -*- coding: utf-8 -*-

import builtins
from typing import List, Optional, Union, Callable, Tuple, Dict, TypeVar, Set, FrozenSet, Type, Generic
from unittest import main, TestCase

from typed import is_instance


class TestIsInstance(TestCase):
    def test_is_instance_builtins(self):
        builtin_types = [t for t in builtins.__dict__.values() if isinstance(t, type)]
        for t in builtin_types:
            try:
                obj = t()
            except (RuntimeError, TypeError):
                continue

            for _t in builtin_types:
                self.assertEqual(isinstance(obj, _t), is_instance(obj, _t))
            self.assertTrue(is_instance(obj, t))
            self.assertTrue(is_instance(t, type))

    def test_is_instance_multiple_types(self):
        self.assertTrue(is_instance([1], (List[str], List[int])))
        self.assertTrue(is_instance(1, (str, int)))
        self.assertFalse(is_instance([1], (List[str], List[bool])))
        self.assertFalse(is_instance(1, (str, bool)))

    def test_is_instance_list(self):
        self.assertTrue(is_instance([1, 2], List))
        self.assertTrue(is_instance([1, 2], List[int]))
        self.assertTrue(is_instance([], List[int]))
        self.assertTrue(is_instance([[1, 2]], List[List[int]]))
        self.assertTrue(is_instance([1, "2"], List[Union[int, str]]))
        self.assertFalse(is_instance([1, "2"], List[int]))
        self.assertFalse(is_instance([1, 2], List[str]))
        self.assertFalse(is_instance([[1, 2]], List[List[str]]))
        self.assertFalse(is_instance(1, List[str]))

    def test_is_instance_union(self):
        self.assertTrue(is_instance([1], Union[List[int], str]))
        self.assertTrue(is_instance("1", Union[int, str]))
        self.assertTrue(is_instance("1", Union[str]))
        self.assertTrue(is_instance(1, Union[int, str]))
        self.assertFalse(is_instance(["1"], Union[List[int], str]))
        self.assertFalse(is_instance(1.1, Union[int, str]))
        self.assertFalse(is_instance(None, Union[int, str]))

    def test_is_instance_optional(self):
        self.assertTrue(is_instance([1], Optional[List[int]]))
        self.assertTrue(is_instance(None, Optional[str]))
        self.assertTrue(is_instance("1", Optional[str]))
        self.assertTrue(is_instance(None, Optional))
        self.assertTrue(is_instance("1", Optional))
        self.assertFalse(is_instance(["1"], Optional[List[int]]))
        self.assertFalse(is_instance("1", Optional[int]))

    def test_is_instance_dict(self):
        self.assertTrue(is_instance({1: "1"}, Dict[int, Union[int, str]]))
        self.assertTrue(is_instance({}, Dict[int, Union[int, str]]))
        self.assertFalse(is_instance({1: None}, Dict[int, Union[int, str]]))
        self.assertFalse(is_instance(None, Dict[int, Union[int, str]]))

    def test_is_instance_tuple(self):
        self.assertTrue(is_instance((1, "1"), Tuple[int, str]))
        self.assertTrue(is_instance((1, "1"), Tuple))
        self.assertTrue(is_instance((1,) * 10, Tuple[int, ...]))
        self.assertFalse(is_instance((1,) * 10, Tuple[str, ...]))
        self.assertFalse(is_instance((1,) * 10, Tuple[int]))
        self.assertFalse(is_instance(("2",) * 10, Tuple[int]))
        self.assertFalse(is_instance([], Tuple))

    def test_is_instance_callable(self):
        def test(_: int) -> None:
            pass

        def test2(*_: int) -> str:
            return ""

        def test3(_: List[Tuple[Optional[int], str]]) -> Optional[int]:
            pass

        self.assertTrue(is_instance(test, Callable[[int], None]))
        self.assertTrue(is_instance(test2, Callable[..., str]))
        self.assertTrue(is_instance(test3, Callable[[List[Tuple[Optional[int], str]]], Optional[int]]))
        self.assertFalse(is_instance(test, Callable[[str], None]))
        self.assertFalse(is_instance(test, Callable[[int], int]))
        self.assertFalse(is_instance(test, Callable[..., None]))
        self.assertFalse(is_instance(test2, Callable[..., None]))
        self.assertFalse(is_instance(test2, Callable[[int], str]))

        # noinspection PyMethodMayBeStatic
        class Dummy:
            def __call__(self, _: int) -> str:
                return ""

            def test1(self, _: int) -> str:
                return ""

            @staticmethod
            def test2(_: int) -> str:
                return ""

            @classmethod
            def test3(cls, _: int) -> str:
                return ""

        d = Dummy()
        for test in (d, d.test1, d.test2, d.test3, Dummy.test2, Dummy.test3):
            self.assertTrue(is_instance(test, Callable[[int], str]))
            self.assertFalse(is_instance(test, Callable[[str], str]))
            self.assertFalse(is_instance(test, Callable[[int], int]))

    def test_is_instance_typevar(self):
        class Animal:
            pass

        class Pet(Animal):
            pass

        class Cat(Pet):
            pass

        animal = Animal()
        pet = Pet()
        cat = Cat()

        # test covariant
        a = TypeVar("a", bool, Pet, covariant=True)
        self.assertFalse(is_instance(None, a))
        self.assertFalse(is_instance(animal, a))
        self.assertTrue(is_instance(pet, a))
        self.assertTrue(is_instance(cat, a))
        self.assertTrue(is_instance(True, a))

        # test contravariant
        b = TypeVar("b", bool, Pet, contravariant=True)
        self.assertFalse(is_instance(None, b))
        self.assertTrue(is_instance(animal, b))
        self.assertTrue(is_instance(pet, b))
        self.assertFalse(is_instance(cat, b))
        self.assertTrue(is_instance(True, b))

        # test invariant
        c = TypeVar("c", bool, Pet)
        self.assertFalse(is_instance(None, c))
        self.assertFalse(is_instance(animal, c))
        self.assertTrue(is_instance(pet, c))
        self.assertFalse(is_instance(cat, c))
        self.assertTrue(is_instance(True, c))

    def test_is_instance_set(self):
        self.assertTrue(is_instance({1, 2}, Set))
        self.assertTrue(is_instance({1, 2}, Set[int]))
        self.assertTrue(is_instance(set(), Set[int]))
        self.assertTrue(is_instance({1, "2"}, Set[Union[int, str]]))
        self.assertFalse(is_instance({1, "2"}, Set[int]))
        self.assertFalse(is_instance({1, 2}, Set[str]))
        self.assertFalse(is_instance(1, Set[str]))

    def test_is_instance_frozenset(self):
        self.assertTrue(is_instance(frozenset([1, 2]), FrozenSet))
        self.assertTrue(is_instance(frozenset([1, 2]), FrozenSet[int]))
        self.assertTrue(is_instance(frozenset(), FrozenSet[int]))
        self.assertTrue(is_instance(frozenset([1, "2"]), FrozenSet[Union[int, str]]))
        self.assertFalse(is_instance(frozenset([1, "2"]), FrozenSet[int]))
        self.assertFalse(is_instance(frozenset([1, 2]), FrozenSet[str]))
        self.assertFalse(is_instance(1, FrozenSet[str]))

    def test_is_instance_type(self):
        class User:
            pass

        class BasicUser(User):
            pass

        self.assertTrue(is_instance(int, Type[int]))
        self.assertTrue(is_instance(BasicUser, Type[BasicUser]))
        self.assertTrue(is_instance(BasicUser, Type[User]))
        self.assertTrue(is_instance(User, Type[User]))
        self.assertFalse(is_instance(User, Type[BasicUser]))

    def test_is_instance_generic(self):
        t = TypeVar('t', int, str)
        a = TypeVar('a', int, str)

        class Dummy(Generic[t]):
            pass

        for obj in (Dummy(), Dummy[int]()):
            self.assertTrue(is_instance(obj, Generic))
            self.assertTrue(is_instance(obj, Dummy))
            self.assertTrue(is_instance(obj, Dummy[t]))
            self.assertTrue(is_instance(obj, Generic[t]))
            self.assertFalse(is_instance(obj, Generic[a]))
            self.assertFalse(is_instance(obj, Dummy[a]))


if __name__ == "__main__":
    main()
