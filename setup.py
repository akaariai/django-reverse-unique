# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="django-reverse-unique",
    version="0.1-dev",
    description="A ReverseUnique field implementation for Django",
    long_description=read('README.rst'),
    url='https://github.com/akaariai/django-reverse-unique',
    license='BSD',
    author='Anssi Kääriäinen',
    author_email='akaariai@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=['reverse_unique']
)
