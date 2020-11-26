"""Library and CLI tools for interacting with RFlink 433MHz transceiver."""

import sys
from codecs import open
from os import path
from subprocess import check_output

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

if sys.version_info < (3, 4):
    raise RuntimeError("This package requires at least Python 3.4")

# Get the long description from the README file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()


def version_from_git():
    """Acquire package version form current git tag."""
    return check_output(
        ["git", "describe", "--tags", "--abbrev=0"], universal_newlines=True
    ).strip()


setup(
    name="rflink",
    version=version_from_git(),
    description=__doc__,
    long_description=long_description,
    # The project's main homepage.
    url="https://github.com/aequitas/python-rflink",
    # Author details
    author="Johan Bloemberg",
    author_email="github@ijohan.nl",
    # Choose your license
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="rflink 433mhz domotica",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    package_data={"rflink": ["py.typed"]},
    install_requires=[
        "async_timeout",
        "docopt",
        "pyserial",
        "pyserial-asyncio",
        'typing;python_version<"3.5"',
    ],
    # # List additional groups of dependencies here (e.g. development
    # # dependencies). You can install these using the following syntax,
    # # for example:
    # # $ pip install -e .[dev,test]
    # extras_require={
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },
    # # If there are data files included in your packages that need to be
    # # installed, specify them here.  If using Python 2.6 or less, then these
    # # have to be included in MANIFEST.in as well.
    # package_data={
    #     'sample': ['package_data.dat'],
    # },
    # # Although 'package_data' is the preferred approach, in some case you may
    # # need to place data files outside of your packages. See:
    # # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        "console_scripts": [
            "rflink=rflink.__main__:main",
            "rflinkproxy=rflinkproxy.__main__:main",
        ],
    },
    project_urls={
        "Release notes": "https://github.com/aequitas/python-rflink/releases",
    },
)
