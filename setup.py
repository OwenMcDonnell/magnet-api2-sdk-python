import io
import codecs
import os
import sys

from setuptools import setup

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

setup(
    name='magnetsdk2',
    description='Python SDK to access the Niddel Magnet API v2',
    long_description=read('README.rst'),
    author='Niddel Corp.',
    author_email='contact@niddel.com',
    version="1.3.1",
    url='http://github.com/mlsecproject/magnet-api2-sdk-python/',
    license='Apache Software License',
    install_requires=['requests>=2.12.5,<3', 'six>=1.10,<2', 'iso8601>=0.1.12,<1',
                      'rfc3987>=1.3.7,<2'],
    tests_require=['pytest>=3.2.5,<4'],
    setup_requires=['pytest-runner>=3,<4'],
    packages=['magnetsdk2'],
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Development Status :: 5 - Production/Stable',
        'Natural Language :: English',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries',
    ],
    entry_points = {
        'console_scripts': ['niddel=magnetsdk2.cli:main']
    }
)
