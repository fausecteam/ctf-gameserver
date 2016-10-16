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
          'markdown',
          'requests',
          'pil',
          'systemd'
      ],
      packages=[
          'ctf_gameserver.checker',
          'ctf_gameserver.lib',
          'ctf_gameserver.web',
          'ctf_gameserver.web.scoring',
          'ctf_gameserver.web.scoring.templatetags',
          'ctf_gameserver.web.registration',
          'ctf_gameserver.web.flatpages',
          'ctf_gameserver.web.templatetags.templatetags',
      ],
      scripts=[
          'checker/ctf-checkermaster',
          'checker/ctf-checkerslave',
          'checker/ctf-logviewer'
          'checker/ctf-testrunner',
          'controller/ctf-controller',
          'controller/ctf-scoring',
          'submission/ctf-submission',
      ],
      data_files=[
          ("/lib/systemd/system", [
              'submission/ctf-submission@.service',
              'checker/ctf-checkermaster@.service',
              'controller/ctf-controller.service',
              'controller/ctf-scoring.service',
              'controller/ctf-controller.timer',
          ]
          ),
          ("/usr/lib/ctf-gameserver/bin/", [
               "web/prod_manage.py",
          ]
          ),
          ("/etc/ctf-gameserver/web/", [
               "web/ctf_gameserver/web/prod_settings.py",
          ]
          ),
          ("/etc/ctf-gameserver/", [
               "controller/controller.conf",
               "controller/scoring.conf",
               "submission/submission.conf",
          ]
          ),
      ],
      package_data={
          "ctf_gameserver.web": ['*/templates/*.html', 'templates/*.html']
      },
      namespace_packages=['ctf_gameserver'],
      package_dir = {'': 'src'},
      license='ISC',
)
