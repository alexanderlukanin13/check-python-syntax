#!/usr/bin/env python

import check_python_syntax

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='check-python-syntax',
    version=check_python_syntax.__version__,
    description='Check Python syntax by compilation (using py_compile)',
    long_description=open('README.rst').read(),
    author='Alexander Lukanin',
    author_email='alexander.lukanin.13@gmail.com',
    url='https://github.com/alexanderlukanin13/check-python-syntax',
    py_modules=['check_python_syntax'],
    scripts=['check_python_syntax.py'],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ),
)