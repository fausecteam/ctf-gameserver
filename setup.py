#!/usr/bin/python3

from setuptools import setup

setup(name='CTF Gameserver',
      version='0.1',
      description='FAUST CTF Gameserver',
      author='Christoph Egger',
      author_email='Christoph.Egger@fau.de',
      url='http://faustctf.net/',
      packages=['ctf_gameserver.checker',
                'ctf_gameserver.checker',
                'ctf_gameserver.lib',
                'ctf_gameserver.web',
                'ctf_gameserver.web.scoring',
                'ctf_gameserver.web.registration',
                'ctf_gameserver.web.flatpages',
                'ctf_gameserver.web.templatetags.templatetags',
            ],
      namespace_packages=['ctf_gameserver'],
      package_dir = {'': 'src'},
      license='MIT',
)
