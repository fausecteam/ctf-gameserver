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
        'ConfigArgParse',
        'Django == 3.2.*',
        'Markdown',
        'Pillow',
        'prometheus_client',
        'pytz',
        'requests',
    ],
    extras_require = {
        'dev': [
            'bandit',
            'mkdocs',
            'psycopg2-binary',
            'pycodestyle',
            'pylint',
            'pytest',
            'pytest-cov',
            'tox'
        ],
        'prod': [
            'psycopg2',
            'systemd'
        ]
    },

    package_dir = {'': 'src'},
    packages = find_packages('src'),
    scripts = [
        'scripts/checker/ctf-checkermaster',
        'scripts/checker/ctf-logviewer',
        'scripts/controller/ctf-controller',
        'scripts/submission/ctf-submission'
    ],
    package_data = {
        'ctf_gameserver.web': [
            '*/templates/*.html',
            '*/templates/*.txt',
            'templates/*.html',
            'templates/*.txt',
            'static/robots.txt',
            'static/*.css',
            'static/*.gif',
            'static/*.js',
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
