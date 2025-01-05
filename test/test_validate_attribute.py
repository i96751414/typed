from typing import Union, Optional, List, Tuple, Dict
from unittest import main, TestCase

from typed import validate_attribute


class TestValidAttribute(TestCase):
    def test_valid_attribute_types(self):
        try:
            validate_attribute("struct", "attribute", type, CustomType)
            validate_attribute("struct", "attribute", object, object())
            validate_attribute("struct", "attribute", int, 1)
            validate_attribute("struct", "attribute", Optional[int], None)
            validate_attribute("struct", "attribute", Union[int, float], 1)
            validate_attribute("struct", "attribute", Union[int, float], 1.0)
            validate_attribute("struct", "attribute", List[bool], [])
            validate_attribute("struct", "attribute", List[bool], [True])
            validate_attribute("struct", "attribute", Tuple[int, float, CustomType], ())
            validate_attribute("struct", "attribute", Tuple[int, float, CustomType], (1, 1.0, CustomType()))
            validate_attribute("struct", "attribute", Dict[str, List[CustomType]], {})
            validate_attribute("struct", "attribute", Dict[str, List[CustomType]], {"k": []})
            validate_attribute("struct", "attribute", Dict[str, List[CustomType]], {"k": [CustomType()]})
            validate_attribute("struct", "attribute", Union[str, List[CustomType], type(None)], "")
            validate_attribute("struct", "attribute", Union[str, List[CustomType], type(None)], [])
            validate_attribute("struct", "attribute", Union[str, List[CustomType], type(None)], [CustomType()])
            validate_attribute("struct", "attribute", Union[str, List[CustomType], type(None)], None)
        except TypeError as e:
            self.fail("test_valid_attribute_types() raised TypeError unexpectedly: {}".format(e))

    def test_invalid_attribute_types(self):
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", type, CustomType())
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", int, "1")
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Optional[int], "None")
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Union[int, float], "1")
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Union[int, float], "1.0")
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", List[bool], True)
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", List[bool], [1])
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Tuple[int, float, CustomType], (1, 1.0))
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Dict[str, List[CustomType]], {"k": [3]})
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Dict[str, List[CustomType]], {3: [CustomType()]})
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Union[str, List[CustomType]], None)
        with self.assertRaises(TypeError):
            validate_attribute("struct", "attribute", Union[str, List[CustomType], type(None)], 1)


class CustomType:
    pass


if __name__ == "__main__":
    main()
