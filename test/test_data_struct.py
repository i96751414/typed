from typing import Dict, List, Union, Optional
from unittest import main, TestCase

from typed import DataStruct


class TestDataStruct(TestCase):
    def test_attributes_listing(self):
        class A(DataStruct):
            attribute_a = DataStruct.attr("a")

        class B(A):
            attribute_b = DataStruct.attr("b")

        self.assertSetEqual({attr[0] for attr in A.attributes()}, {"a"})
        self.assertSetEqual({attr[0] for attr in B.attributes()}, {"a", "b"})

    def test_from_dict(self):
        class A(DataStruct):
            var_1 = DataStruct.attr("var1", int)

        class B(DataStruct):
            child = DataStruct.attr("child", A)
            child_dict = DataStruct.attr("child_dict", Dict[str, A])
            child_list = DataStruct.attr("child_list", List[A])
            child_union = DataStruct.attr("child_union", Union[A, int])

        b = B.from_dict(dict(child=dict(var1=1), child_dict={"A": A(var_1=2)}, child_list=[A(var_1=3)], child_union=4))

        self.assertIsInstance(b.child, A)
        self.assertEqual(b.child.var_1, 1)

        self.assertIsInstance(b.child_dict, dict)
        self.assertEqual(len(b.child_dict), 1)
        self.assertIsInstance(b.child_dict.get("A"), A)

        self.assertIsInstance(b.child_list, list)
        self.assertEqual(len(b.child_list), 1)
        self.assertIsInstance(b.child_list[0], A)

        self.assertEqual(b.child_union, 4)

    def test_from_dict_strict(self):
        class A(DataStruct):
            var_1 = DataStruct.attr("var1", int)

        with self.assertRaises(ValueError):
            A.from_dict(dict(var_1=1, var_2=2))

    def test_from_dict_no_types(self):
        class A(DataStruct):
            var_1 = DataStruct.attr("var1")
            var_2 = DataStruct.attr("var2", default="var2")
            var_3 = DataStruct.attr("var3", default=None, from_converter=lambda _: "var3")
            var_4 = DataStruct.attr("var4", default=None, from_converter=lambda _: "var4")

        a = A.from_dict(dict(var1=1, var4=None))

        self.assertEqual(a.var_1, 1)
        self.assertEqual(a.var_2, "var2")
        self.assertIsNone(a.var_3)
        self.assertEqual(a.var_4, "var4")

    def test_missing_value(self):
        class A(DataStruct):
            missing = DataStruct.attr("missing", str)

        with self.assertRaises(ValueError):
            A.from_dict({})

    def test_default_value(self):
        class A(DataStruct):
            missing = DataStruct.attr("missing", str, default="default")

        self.assertEqual(A.from_dict({}).missing, "default")
        self.assertEqual(A.from_dict(dict(missing="")).missing, "")

    def test_nullable_values(self):
        class A(DataStruct):
            val_1 = DataStruct.attr("val_1", Optional[str])
            val_2 = DataStruct.attr("val_2", str, default=None)

        try:
            A.from_dict(dict(val_1=None, val_2=None))
        except ValueError:
            self.fail("from_dict() raised ValueError unexpectedly")

    def test_converter(self):
        class A(DataStruct):
            val_1 = DataStruct.attr("val_1", str, from_converter=lambda v: v + ".")
            val_2 = DataStruct.attr("val_2", str, from_converter=lambda _: "new value 2")
            val_3 = DataStruct.attr("val_3", Optional[str], from_converter=lambda _: "new value 3")

        a = A.from_dict(dict(val_1="old value 1", val_2=None, val_3=None))
        self.assertEqual(a.val_1, "old value 1.")
        self.assertEqual(a.val_2, "new value 2")
        self.assertIsNone(a.val_3)


if __name__ == "__main__":
    main()
