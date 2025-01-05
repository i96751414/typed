from typing import Optional, Union
from unittest import main, TestCase

from typed import is_nullable


class TestIsNullable(TestCase):
    def test_nullable_types(self):
        self.assertTrue(is_nullable(Optional[int]))
        self.assertTrue(is_nullable(Union[int, type(None)]))
        self.assertTrue(is_nullable(type(None)))

    def test_non_nullable_types(self):
        self.assertFalse(is_nullable(Optional))
        self.assertFalse(is_nullable(int))
        self.assertFalse(is_nullable(Union[int, str]))


if __name__ == "__main__":
    main()
