from __future__ import print_function
import codecs
import os
import sys

from setuptools import setup
from setuptools.command.test import test as testcommand

here = os.path.abspath(os.path.dirname(__file__))

# Version info
__version_info__ = (0, 1, 0)
__version__ = ".".join(map(str, __version_info__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


long_description = read('README.md')


class PyTest(testcommand):
    # noinspection PyAttributeOutsideInit
    def finalize_options(self):
        testcommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


setup(
    name='magnetsdk',
    description='Python SDK to the Niddel Magnet API v2',
    long_description=long_description,
    author='Niddel Corp.',
    author_email='contact@niddel.com',
    version=__version__,
    url='http://github.com/mlsecproject/magnet-api2-sdk-python/',
    license='Apache Software License',
    install_requires=['requests==2.18.3', 'six>=1.10,<2', 'iso8601>=0.1.12,<1', 'rfc3987>=1.3.7,<2', 'pytz'],
    tests_require=['pytest'],
    test_suite='magnetsdk.test.test_magnetsdk',
    cmdclass={'test': PyTest},
    packages=['magnetsdk'],
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
    ],
    extras_require={
        'testing': ['pytest', 'iso8601'],
    }
)
