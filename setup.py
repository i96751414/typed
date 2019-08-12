#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from setuptools import setup

__version__ = "0.0.1"

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="typed",
    version=__version__,
    description="A very simple library which provides methods for "
                "type checking along with runtime type hint validation.",
    long_description=long_description,
    license="GPLv3",
    author="i96751414",
    author_email="i96751414@gmail.com",
    py_modules=["typed"],
    python_requires=">=3.5",
)
