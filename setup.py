# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

VERSION = (0, 5, 8)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

setup(
    name='sq-subscribe',
    version=__versionstr__,
    description="sq_subscribe описание",
    author='SevenQuark',
    author_email='info@sevenquark.com',
    url='http://www.sevenquark.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
