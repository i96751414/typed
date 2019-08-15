#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Callable, List
from unittest import main, TestCase

from typed import is_instance, checked, type_checked


class TestDecorators(TestCase):
    def test_is_instance_callable(self):
        @type_checked
        def test_type_checked(_: int) -> bool:
            pass

        @checked
        def test_checked(_: List[int]) -> None:
            pass

        @type_checked
        class DummyTypeChecked:
            def test(self, _: int) -> None:
                pass

        @checked
        class DummyChecked:
            def test(self, _: int) -> None:
                pass

        self.assertTrue(is_instance(test_type_checked, Callable[[int], bool]))
        self.assertTrue(is_instance(test_checked, Callable[[List[int]], None]))
        self.assertTrue(is_instance(DummyTypeChecked().test, Callable[[int], None]))
        self.assertTrue(is_instance(DummyChecked().test, Callable[[int], None]))

    # noinspection PyTypeChecker
    def test_checked_decorator(self):
        @checked
        def test(a: List[int], b: str, c: int = 1, *d: str, e: float = 1.1, f: bool, **g: int):
            self.assertTrue(is_instance(a, List[int]))
            self.assertTrue(is_instance(b, str))
            self.assertTrue(is_instance(c, int))
            for _d in d:
                self.assertTrue(is_instance(_d, str))
            self.assertTrue(is_instance(e, float))
            self.assertTrue(is_instance(f, bool))
            for _g in g.values():
                self.assertTrue(is_instance(_g, int))

        test([1], "b", 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test(["1"], "b", 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], 1, 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", "1", "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, 1, "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", 1, e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e="2.2", f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=1, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=False, g="444", h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=False, g=444, h="111")

    # noinspection PyTypeChecker
    def test_type_checked_decorator(self):
        @type_checked
        def test(a: list, b: str, c: int = 1, *d: str, e: float = 1.1, f: bool, **g: int):
            self.assertTrue(isinstance(a, list))
            self.assertTrue(isinstance(b, str))
            self.assertTrue(isinstance(c, int))
            for _d in d:
                self.assertTrue(isinstance(_d, str))
            self.assertTrue(isinstance(e, float))
            self.assertTrue(isinstance(f, bool))
            for _g in g.values():
                self.assertTrue(isinstance(_g, int))

        test([1], "b", 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test(1, "b", 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], 1, 1, "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", "1", "a", "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, 1, "b", e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", 1, e=2.2, f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e="2.2", f=False, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=1, g=444, h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=False, g="444", h=111)
        with self.assertRaises(TypeError):
            test([1], "b", 1, "a", "b", e=2.2, f=False, g=444, h="111")

    # noinspection PyTypeChecker
    def test_checked_class_decorator(self):
        # noinspection PyMethodParameters,PyMethodMayBeStatic
        @checked
        class DummyChecked1:
            def test1(_, a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            @staticmethod
            def test2(a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            @classmethod
            def test3(_, a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            class TestClass:
                @staticmethod
                def test4(a: List[int]):
                    self.assertTrue(is_instance(a, List[int]))

        d1 = DummyChecked1()
        for func in (d1.test1, d1.test2, d1.test3, d1.TestClass.test4,
                     DummyChecked1.test2, DummyChecked1.test3, DummyChecked1.TestClass.test4):
            func([1])
            with self.assertRaises(TypeError):
                func("1")

        # noinspection PyMethodParameters,PyMethodMayBeStatic,PyNestedDecorators
        class DummyChecked2:
            @checked
            def test1(_, a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            @staticmethod
            @checked
            def test2(a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            # Although this is not the correct way of doing it, lets test it.
            @checked
            @staticmethod
            def test3(a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            @classmethod
            @checked
            def test4(_, a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            # Although this is not the correct way of doing it, lets test it.
            @checked
            @classmethod
            def test5(_, a: List[int]):
                self.assertTrue(is_instance(a, List[int]))

            def test6(_, a: int):
                self.assertFalse(is_instance(a, int))

        d2 = DummyChecked2()
        for func in (d2.test1, d2.test2, d2.test3, d2.test4, d2.test5,
                     DummyChecked2.test3, DummyChecked2.test4, DummyChecked2.test5):
            func([1])
            with self.assertRaises(TypeError):
                func(1)
        d2.test6("1")

    # noinspection PyTypeChecker
    def test_type_checked_class_decorator(self):
        # noinspection PyMethodParameters,PyMethodMayBeStatic
        @type_checked
        class DummyTypeChecked1:
            def test1(_, a: int):
                self.assertTrue(isinstance(a, int))

            @staticmethod
            def test2(a: int):
                self.assertTrue(isinstance(a, int))

            @classmethod
            def test3(_, a: int):
                self.assertTrue(isinstance(a, int))

            class TestClass:
                @staticmethod
                def test4(a: int):
                    self.assertTrue(isinstance(a, int))

        d1 = DummyTypeChecked1()
        for func in (d1.test1, d1.test2, d1.test3, d1.TestClass.test4,
                     DummyTypeChecked1.test2, DummyTypeChecked1.test3, DummyTypeChecked1.TestClass.test4):
            func(1)
            with self.assertRaises(TypeError):
                func("1")

        # noinspection PyMethodParameters,PyMethodMayBeStatic,PyNestedDecorators
        class DummyTypeChecked2:
            @type_checked
            def test1(_, a: int):
                self.assertTrue(isinstance(a, int))

            @staticmethod
            @type_checked
            def test2(a: int):
                self.assertTrue(isinstance(a, int))

            # Although this is not the correct way of doing it, lets test it.
            @type_checked
            @staticmethod
            def test3(a: int):
                self.assertTrue(isinstance(a, int))

            @classmethod
            @type_checked
            def test4(_, a: int):
                self.assertTrue(isinstance(a, int))

            # Although this is not the correct way of doing it, lets test it.
            @type_checked
            @classmethod
            def test5(_, a: int):
                self.assertTrue(isinstance(a, int))

            def test6(_, a: int):
                self.assertFalse(isinstance(a, int))

        d2 = DummyTypeChecked2()
        for func in (d2.test1, d2.test2, d2.test3, d2.test4, d2.test5,
                     DummyTypeChecked2.test3, DummyTypeChecked2.test4, DummyTypeChecked2.test5):
            func(1)
            with self.assertRaises(TypeError):
                func("1")
        d2.test6("1")


if __name__ == "__main__":
    main()
