#!/usr/bin/env python3

import os

from setuptools import setup, find_packages


setup(
    name = 'ctf_gameserver',
    description = 'FAUST CTF Gameserver',
    url = 'http://ctf-gameserver.org',
    version = '1.0',
    author = 'Christoph Egger, Felix Dreissig',
    author_email = 'christoph.egger@fau.de, f30@f30.me',
    license = 'ISC',

    install_requires = [
        'Django==1.11.*',
        'Markdown',
        'Pillow',
        'pytz',
        'psycopg2',
        'requests',
        # TODO: Make this platform independent for development
        #'systemd'
    ],

    package_dir = {'': 'src'},
    packages = find_packages('src'),
    scripts = [
        'scripts/checker/ctf-checkermaster',
        'scripts/checker/ctf-checkerslave',
        'scripts/checker/ctf-logviewer',
        'scripts/checker/ctf-testrunner',
        'scripts/controller/ctf-controller',
        'scripts/controller/ctf-flagid',
        'scripts/controller/ctf-scoring',
        'scripts/submission/ctf-submission'
    ],
    package_data = {
        'ctf_gameserver.web': [
            '*/templates/*.html',
            '*/templates/*.txt',
            'templates/*.html',
            'templates/*.txt',
            'static/robots.txt',
            'static/style.css',
            'static/ext/jquery.min.js',
            'static/ext/bootstrap/css/*',
            'static/ext/bootstrap/fonts/*',
            'static/ext/bootstrap/js/*'
        ],
        'ctf_gameserver.web.registration': [
            'countries.csv'
        ]
    }
)
