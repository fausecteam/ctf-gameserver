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

Website
-------

The web part is a standard django webapplication. For the example
setup we use uwsgi and nginx to serve it and example configuration is
provided with the software. From the gameserver the package
``ctf-gameserver-web`` is needed. In the
``/etc/ctf-gameserver/web/prod_settings`` the following keys need
adaption: ``SECRET_KEY``, ``ALLOWED_HOSTS``, ``DATABASES`` and
``TIME_ZONE``. For the ``prod_manage.py`` utility add
``/usr/lib/ctf-gameserver/bin`` to your ``PATH``.

.. code-block:: bash

   PYTHONPATH=/etc/ctf-gameserver/web django-admin migrate --settings prod_settings auth
   PYTHONPATH=/etc/ctf-gameserver/web django-admin migrate --settings prod_settings

.. note::

   the default production settings also use memcached. Proper setup of
   memcached should be covered here. For small CTFs it should be
   enough to switch back to the dummycache from the development settings

.. note::

   setup.py does not install the external javascript dependencies. The
   files needs to be downloaded. Please refer to ``web/Makefile`` in the
   source tree for details.

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

Checker
-------

Put a service description into ``/etc/ctf-gameserver`` and the python
checker module into ``/etc/ctf-gameserver/checker`` for each service
in the ctf. After installing ``ctf-gameserver-controller`` you can
then enable the checkers with ``systemctl enable
ctf-checkermaster@exampleservice``. For advice on how the service
description is supposed to look like please refer to the provided
examples.

Scoring
-------

The gameserver comes with an example scoring function. If you want to
use it, apply the ``scoring.sql`` patch to the database. The
ctf-scoring unit will take care of periodically updating the
score. You can implement your own scoring either by adapting the SQL
for the materialized view in ``scoring.sql`` or by writing your
scoring code to the ``ctf-scoring`` programm. Scoring needs to create
a table or view with the schema produced below and contain a row for
every team.

.. code-block:: sql

    CREATE TABLE "scoring_scoreboard" (
      "team_id" integer NOT NULL,
      "attack" integer NOT NULL,
      "bonus" integer NOT NULL,
      "defense" double precision NOT NULL,
      "sla" double precision NOT NULL,
      "total" double precision NOT NULL,
      PRIMARY KEY (team_id, service_id, identifier)
    );

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
