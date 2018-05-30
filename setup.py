#!/usr/bin/python3

from setuptools import setup
from setuptools.command.install import install
import glob
import os.path


class ctf_gameserver_install(install):
    _servicefiles = [
        'submission/ctf-submission@.service',
        'checker/ctf-checkermaster@.service',
        'controller/ctf-controller.service',
        'controller/ctf-scoring.service',
        ]

    def run(self):
        install.run(self)

        if not self.dry_run:
            bindir = self.install_scripts
            if bindir.startswith(self.root):
                bindir = bindir[len(self.root):]

            systemddir = os.path.join(self.root, "lib/systemd/system")

            for servicefile in self._servicefiles:
                service = os.path.split(servicefile)[1]
                self.announce("Creating %s" % os.path.join(systemddir, service),
                              level=2)
                with open(servicefile) as servicefd:
                    servicedata = servicefd.read()

                with open(os.path.join(systemddir, service), "w") as servicefd:
                    servicefd.write(servicedata.replace("%BINDIR%", bindir))


setup(name='CTF Gameserver',
      include_package_data=True,
      version='0.1-rc0',
      description='FAUST CTF Gameserver',
      author='Christoph Egger, Felix Dreissig',
      author_email='Christoph.Egger@fau.de, Felix.Dreissig@fau.de',
      url='http://ctf-gameserver.faust.ninja/',
      license='ISC',
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
          'ctf_gameserver.submission',
          'ctf_gameserver.web',
          'ctf_gameserver.web.flatpages',
          'ctf_gameserver.web.registration',
          'ctf_gameserver.web.scoring',
          'ctf_gameserver.web.scoring.templatetags',
          'ctf_gameserver.web.templatetags.templatetags',
      ],
      scripts=[
          'checker/ctf-checkermaster',
          'checker/ctf-checkerslave',
          'checker/ctf-logviewer',
          'checker/ctf-testrunner',
          'controller/ctf-controller',
          'controller/ctf-flagid',
          'controller/ctf-scoring',
          'submission/ctf-submission',
      ],
      data_files=[
          ("/lib/systemd/system", [
              'controller/ctf-controller.timer',
          ]
          ),
          ("/etc/ctf-gameserver/web/", [
               "web/ctf_gameserver/web/prod_settings.py",
          ]
          ),
          ("/etc/ctf-gameserver/", [
               "checker/checkermaster.conf",
               "controller/controller.conf",
               "controller/scoring.conf",
               "controller/flagid.conf",
               "submission/submission.conf",
          ]
          ),
      ],
      package_data={
          "ctf_gameserver.web": ['*/templates/*.html', 'templates/*.html', 'static/style.css',
                                 'registration/countries.csv']
      },
      namespace_packages=['ctf_gameserver'],
      package_dir = {'': 'src'},
      test_suite = 'run_tests.all_the_tests',
      cmdclass={'install': ctf_gameserver_install},
)
