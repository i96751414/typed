from typing import Union, Optional, List, Tuple, Dict
from unittest import main, TestCase

from typed import validate_attribute_type


class TestValidAttributeType(TestCase):
    def test_valid_types(self):
        try:
            validate_attribute_type("attribute_name", type)
            validate_attribute_type("attribute_name", object)
            validate_attribute_type("attribute_name", int)
            validate_attribute_type("attribute_name", Optional[int])
            validate_attribute_type("attribute_name", Union[int, float])
            validate_attribute_type("attribute_name", List[bool])
            validate_attribute_type("attribute_name", Tuple[int, float, CustomType])
            validate_attribute_type("attribute_name", Dict[str, List[CustomType]])
            validate_attribute_type("attribute_name", Union[str, List[CustomType], type(None)])
        except TypeError as e:
            self.fail("validate_attribute_type() raised TypeError unexpectedly: {}".format(e))

    def test_non_hashable_dict_key(self):
        with self.assertRaises(TypeError):
            validate_attribute_type("attribute_name", Dict[List[int], int])
        with self.assertRaises(TypeError):
            validate_attribute_type("attribute_name", Dict[Union[List[int], str], int])

    def test_invalid_types(self):
        with self.assertRaises(TypeError):
            validate_attribute_type("attribute_name", 1)
        with self.assertRaises(TypeError):
            validate_attribute_type("attribute_name", object())


class CustomType:
    pass


if __name__ == "__main__":
    main()
