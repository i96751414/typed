#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
from unittest import main, TestCase

from typed import type_repr


class TestTypeRepr(TestCase):
    def test_type_repr_list(self):
        self.assertEqual(type_repr([]), "List")
        self.assertEqual(type_repr([1]), "List[int]")
        self.assertEqual(type_repr([1, 1]), "List[int]")
        self.assertEqual(type_repr([1, ""]), "List[Union[int, str]]")

    def test_type_repr_tuple(self):
        self.assertEqual(type_repr(tuple()), "Tuple[()]")
        self.assertEqual(type_repr((1,)), "Tuple[int]")
        self.assertEqual(type_repr((1, 1)), "Tuple[int, ...]")
        self.assertEqual(type_repr((1, 1, 1)), "Tuple[int, ...]")
        self.assertEqual(type_repr((1, "")), "Tuple[int, str]")

    def test_type_repr_dict(self):
        self.assertEqual(type_repr({}), "Dict")
        self.assertEqual(type_repr({1: 1}), "Dict[int, int]")
        self.assertEqual(type_repr({1: 1, 2: "2"}), "Dict[int, Union[int, str]]")
        self.assertEqual(type_repr({1: 1, "2": 2}), "Dict[Union[int, str], int]")

    def test_type_repr_callable(self):
        def test1(_: int) -> str:
            pass

        def test2(*_: int) -> typing.Optional[str]:
            return ""

        def test3(_: typing.List[str]) -> str:
            pass

        def test4(**_: str) -> int:
            pass

        def test5(_: bool, *__: int, **___: str) -> typing.Dict[str, typing.Union[int, str]]:
            pass

        self.assertEqual(type_repr(test1), "Callable[[int], str]")
        self.assertIn(type_repr(test2), "Callable[..., Optional[str]]")
        self.assertEqual(type_repr(test3), "Callable[[List[str]], str]")
        self.assertEqual(type_repr(test4), "Callable[..., int]")
        self.assertEqual(type_repr(test5), "Callable[..., Dict[str, Union[int, str]]]")

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
        for func in (d.test1, d.test2, d.test3):
            self.assertEqual(type_repr(func), "Callable[[int], str]")

    def test_type_repr_set(self):
        self.assertEqual(type_repr(set()), "Set")
        self.assertEqual(type_repr({1}), "Set[int]")
        self.assertEqual(type_repr({1, 1}), "Set[int]")
        self.assertEqual(type_repr({1, ""}), "Set[Union[int, str]]")

    def test_type_repr_frozenset(self):
        self.assertEqual(type_repr(frozenset()), "FrozenSet")
        self.assertEqual(type_repr(frozenset([1])), "FrozenSet[int]")
        self.assertEqual(type_repr(frozenset([1, 1])), "FrozenSet[int]")
        self.assertEqual(type_repr(frozenset([1, ""])), "FrozenSet[Union[int, str]]")

    def test_type_repr_type(self):
        self.assertEqual(type_repr(int), "Type[int]")


if __name__ == "__main__":
    main()
