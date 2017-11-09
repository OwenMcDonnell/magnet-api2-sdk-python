from __future__ import print_function

from pypandoc import convert_file
from setuptools import setup

from magnetsdk2.version import __version__

long_description = convert_file('README.md', 'rst')

setup(
    name='magnetsdk2',
    description='Python SDK to access the Niddel Magnet API v2',
    long_description=long_description,
    author='Niddel Corp.',
    author_email='contact@niddel.com',
    version=__version__,
    url='http://github.com/mlsecproject/magnet-api2-sdk-python/',
    license='Apache Software License',
    install_requires=['requests>=2.12.5,<3', 'six>=1.10,<2', 'iso8601>=0.1.12,<1', 'rfc3987>=1.3.7,<2'],
    packages=['magnetsdk2'],
    include_package_data=True,
    platforms='any',
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ]
)
