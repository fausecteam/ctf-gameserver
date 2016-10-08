Gameserver Setup
================

For the setup instructions we consider a clean debian stable install
on all machines. All components can be installed on separate machines
or all on one single node but should share a common (firewalled)
network. We further assume that postgresql has been installed on a
machine on that network. ctf-gameserver has been checked out and built
(dpkg-buildpackage -b).

.. code-block:: bash

   createuser -P faustctf
   createdb -O faustctf faustctf
   createdb -O faustctf checkercache

Website
-------

The web part is a standard django webapplication. For the example
setup we use uwsgi and nginx to serve it and example configuration is
provided with the software. From the gameserver the package
``ctf-gameserver-web`` is needed. In the prod_settings the following
keys need adaption: ``SECRET_KEY``, ``ALLOWED_HOSTS``, ``DATABASES``
and ``TIME_ZONE``.

.. code-block:: bash

   ./prod_manage.py migrate auth
   ./prod_manage.py migrate

.. note::

   the default production settings also use memcached. Proper setup of
   memcached should be covered here. For small CTFs it should be
   enough to switch back to the dummycache from the development settings

.. note::

   setup.py does not install ``countrynames.txt``.

.. note::

   ``prod_settings.py`` is part of the installed tree and needs to be
   modified there

.. note::
	  
   ``prod_manage.py`` is not installed by setup.py at all and needs to
   be copied over manually

Submission and Controller
-------------------------

Install the packages ``ctf-gameserver-controller`` and
``ctf-gameserver-submission``. The controller should now be working
(it's a systemd timer unit), the submission service needs explicit
activation with ``systemctl enable ctf-submission@1234`` where
``1234`` is the port submission should be listening on. One needs to
use a portnumber above 1000. One can easily run more than one
submission service and even use iptables to do some loadbalancing. The
submission server is using an event-based architecture and is
single-threaded.

The database for the checkercache needs to be set up manually and
should contain exactly one table:

.. code-block:: sql

   CREATE TABLE checkercache (
     team_id INTEGER,
     service_id INTEGER,
     identifier CHARACTER VARYING (128),
     data BYTEA);

Checker
-------

Put a service description into ``/etc/ctf-gameserver`` and the python
checker module into ``/etc/ctf-gameserver/checker`` for each service
in the ctf. After installing ``ctf-gameserver-controller`` you can
then enable the checkers with ``systemctl enable
ctf-checkermaster@exampleservice``. For advice on how the service
description is supposed to look like please refer to the provided
examples.

.. note::

   Currently it is necessary to manually switch to the contestchecker
   TODO reconfigure checkermodule for contest in the ``__init__.py``
   for :py:mod:`ctf_gameserver.checker`

Networking
----------

This section will detail some suggestions for the network setup of the
CTF.

* All Team members need to reach the submission system and the
  submission system needs to observe the unmodified source ip from the
  teams. If there is any NAT in place care must be taken to ensoure
  the translated address still matches the Team network.
* Commonly all traffic reaching out to the vulnboxes are NAT'ed to
  hide the real source-IP and thereby making it more difficult to
  distinguish between checkers and attackers based on network
  properties.
* All ``ctf-gameserver`` components need to reach the database. Noone
  else does and it is a good idea to isolate the database from such
  access.
