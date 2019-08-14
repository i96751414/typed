<h1 align="center">
  <img alt="packet" src="https://www.python.org/static/opengraph-icon-200x200.png" width="200px" height="200px"/>
  <br/>
  typed
</h1>
<p align="center">A very simple library which provides methods for type checking along with runtime type hint validation.</p>
<div align="center">
  <a href="https://travis-ci.org/i96751414/typed"><img alt="Build Status" src="https://travis-ci.org/i96751414/typed.svg?branch=master" /></a>
  <a href="https://www.gnu.org/licenses/"><img alt="License" src="https://img.shields.io/:license-GPL--3.0-blue.svg?style=flat" /></a>
</div>
<br/>

This module performs runtime type hint validation using [typing](https://docs.python.org/3/library/typing.html) type hints.
It also includes some utilities such as `is_instance`, for checking the object instance, and `type_repr`, for generating a string representation of an object type.

## Decorators

Two decorators are provided in order to perform runtime type hint validation: `checked` and `type_checked`. These can be applied to either functions or classes.
The main difference between them is that `checked` uses the custom implementation `is_instance` whereas `type_checked` uses the default `isinstance` (making it only support default types).

```python
from typing import List
from typed import checked

@checked
def foo(a: List[int]):
    pass

foo([1])  # This is OK
foo(["1"])  # This raises TypeError
```
