#!/usr/bin/python

# Copyright 2020 Lou King
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# run from directory above setup.py, e.g.,
#    python -m running.setup install sdist bdist_wheel

# home grown
from running import version

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name = "runtilities",
    version = version.__version__,
    packages = find_packages(),
    long_description = long_description,
    long_description_content_type = 'text/markdown',

    scripts = [
        'running/analyzeagegrade.py',
        'running/athlinksresults.py',
        'running/competitor2csv.py',
        'running/parseresults.py',
        'running/parsetcx.py',
        'running/renderclubagstats.py',
        'running/runningaheadresults.py',
        # 'running/strava.py',
        'running/ultrasignupresults.py',
    ],
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    # install_requires tailored for runsignup.py
    install_requires = [
        'requests>=2.22.0',
        'requests_oauthlib>=1.3.0',
        'loutilities>=3.0.0',
        'tzlocal>=2.0.0',
        'xlrd>=1.2.0',
        'unicodecsv>=0.14.1',
        'sqlalchemy>=1.3.12',
        # 'matplotlib>=1.1.1', # not available on godaddy
        # 'pykml>=0.1.0',       # lxml not available on godaddy
        # 'lxml>=2.3',          # lxml not available on godaddy
        ],

    entry_points = {
        'console_scripts': [
            'analyzeagegrade = running.analyzeagegrade:main',
            'athlinksresults = running.athlinksresults:main',
            'competitor2csv = running.competitor2csv:main',
            'parseresults = running.parseresults:main',
            'parsetcx = running.parsetcx:main',
            'renderclubagstats = running.renderclubagstats:main',
            'runningaheadresults = running.runningaheadresults:main',
            'ultrasignupresults = running.ultrasignupresults:main',
            # 'updatestravaclubactivitycache = running.strava:updatestravaclubactivitycache'
        ],
    },

    zip_safe = False,

    # metadata for upload to PyPI
    description = 'running related scripts',
    author = 'Lou King',
    author_email = 'lking@pobox.com',
    url = 'http://github.com/louking/running',
    # could also include download_url, etc.
)

