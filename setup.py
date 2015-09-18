import os
import platform
import re
import sys
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError
from distutils.errors import DistutilsExecError
from distutils.errors import DistutilsPlatformError
from setuptools import Distribution as _Distribution, Extension
from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand

try:
    import vsc.install.shared_setup as shared_setup
    from vsc.install.shared_setup import ag
except ImportError:
    print "vsc.install could not be found, make sure a recent vsc-base is installed"
    print "you might want to try 'easy_install [--user] https://github.com/hpcugent/vsc-base/archive/master.tar.gz'"


def remove_bdist_rpm_source_file():
    """List of files to remove from the (source) RPM."""
    return ['lib/vsc/__init__.py']


shared_setup.remove_extra_bdist_rpm_files = remove_bdist_rpm_source_file
shared_setup.SHARED_TARGET.update({
    'url': 'https://github.ugent.be/hpcugent/vsc-config',
    'download_url': 'https://github.ugent.be/hpcugent/vsc-config'
})


cmdclass = {}
if sys.version_info < (2, 6):
    raise Exception("SQLAlchemy requires Python 2.6 or higher.")

cpython = platform.python_implementation() == 'CPython'

ext_modules = [
    Extension('sqlalchemy.cprocessors',
              sources=['lib/sqlalchemy/cextension/processors.c']),
    Extension('sqlalchemy.cresultproxy',
              sources=['lib/sqlalchemy/cextension/resultproxy.c']),
    Extension('sqlalchemy.cutils',
              sources=['lib/sqlalchemy/cextension/utils.c'])
]

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)
if sys.platform == 'win32':
    # 2.6's distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    ext_errors += (IOError,)


class BuildFailed(Exception):

    def __init__(self):
        self.cause = sys.exc_info()[1]  # work around py 2/3 different syntax


class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()
        except ValueError:
            # this can happen on Windows 64 bit, see Python issue 7511
            if "'path'" in str(sys.exc_info()[1]):  # works with both py 2/3
                raise BuildFailed()
            raise

cmdclass['build_ext'] = ve_build_ext


class Distribution(_Distribution):

    def has_ext_modules(self):
        # We want to always claim that we have ext_modules. This will be fine
        # if we don't actually have them (such as on PyPy) because nothing
        # will get built, however we don't want to provide an overally broad
        # Wheel package when building a wheel without C support. This will
        # ensure that Wheel knows to treat us as if the build output is
        # platform specific.
        return True


class PyTest(TestCommand):
    # from https://pytest.org/latest/goodpractises.html\
    # #integration-with-setuptools-test-commands
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    default_options = ["-n", "4", "-q"]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(
            " ".join(self.default_options) + " " + self.pytest_args)
        sys.exit(errno)

cmdclass['test'] = PyTest


def status_msgs(*msgs):
    print('*' * 75)
    for msg in msgs:
        print(msg)
    print('*' * 75)


with open(
        os.path.join(
            os.path.dirname(__file__),
            'lib', 'sqlalchemy', '__init__.py')) as v_file:
    VERSION = re.compile(
        r".*__version__ = '(.*?)'",
        re.S).match(v_file.read()).group(1)

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as r_file:
    readme = r_file.read()


PACKAGE = {
    "name": "sqlalchemy",
    "version": VERSION,
    "description": "Database Abstraction Library",
    "author": ["Mike Bayer",],
    "author_email": "mike_mp@zzzcomputing.com",
    "maintainer": [ag,],
    "url": "http://www.sqlalchemy.org",
    "packages": find_packages('lib'),
    "package_dir": {'': 'lib'},
    "license": "MIT License",
    "cmdclass": cmdclass,
    "tests_require": ['pytest >= 2.5.2', 'mock', 'pytest-xdist'],
    "long_description": readme,
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: Jython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent",
    ],
}
shared_setup.action_target(PACKAGE)
