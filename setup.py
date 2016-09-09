#!/usr/bin/python3

from setuptools import setup

setup(name='CTF Gameserver',
      include_package_data=True,
      version='0.1-rc0',
      description='FAUST CTF Gameserver',
      author='Christoph Egger, Felix Dreissig',
      author_email='Christoph.Egger@fau.de, Felix.Dreissig@fau.de',
      url='http://faustctf.net/',
      install_requires=[
          'psycopg2',
          'django',
      ],
      packages=[
          'ctf_gameserver.checker',
          'ctf_gameserver.lib',
          'ctf_gameserver.web',
          'ctf_gameserver.web.scoring',
          'ctf_gameserver.web.registration',
          'ctf_gameserver.web.flatpages',
          'ctf_gameserver.web.templatetags.templatetags',
      ],
      scripts=[
          'controller/ctf-controller',
          'checker/ctf-checkermaster',
          'checker/ctf-checkerslave',
          'checker/ctf-testrunner',
          'submission/ctf-submission',
      ],
      data_files=[
          ("/lib/systemd/system", [
              'submission/ctf-submission@.service',
              'checker/ctf-checkermaster@.service',
              'controller/ctf-controller.service',
              'controller/ctf-controller.timer',
          ]
       )
      ],
      package_data={
          "": ['doc/Makefile',
               'doc/source/*.rst',
           ]
      },
      namespace_packages=['ctf_gameserver'],
      package_dir = {'': 'src'},
      license='ISC',
)
