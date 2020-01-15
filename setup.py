#!/usr/bin/python

# Copyright 2013 Lou King
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

import ez_setup
import glob
import pdb

# home grown
from . import version

ez_setup.use_setuptools()
from setuptools import setup, find_packages

setup(
    name = "running",
    version = version.__version__,
    packages = find_packages(),

    scripts = [
        'running/analyzeagegrade.py',
        'running/athlinksresults.py',
        'running/competitor2csv.py',
        'running/parseresults.py',
        'running/parsetcx.py',
        'running/renderclubagstats.py',
        'running/runningaheadresults.py',
        'running/strava.py',
        'running/ultrasignupresults.py',
    ],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires = [
        # 'matplotlib>=1.1.1', # not available on godaddy
        'loutilities>=0.14.9',
        'xlrd>=0.8.0',   
        # 'pykml>=0.1.0',       # lxml not available on godaddy
        'gpxpy>=0.7.0',
        # 'lxml>=2.3',          # lxml not available on godaddy
        'httplib2>=0.7.7',
        ],

    # If any package contains any of these file types, include them:
    package_data = ([
        ]),

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
            'updatestravaclubactivitycache = running.strava:updatestravaclubactivitycache'
        ],
    },

    zip_safe = False,

    # metadata for upload to PyPI
    description = 'general purpose running related scripts',
    license = 'Apache License, Version 2.0',
    author = 'Lou King',
    author_email = 'lking@pobox.com',
    url = 'http://github.com/louking/running',
    # could also include long_description, download_url, classifiers, etc.
)

