General
-------

Database
========

Configuration
=============

All configuration files are stored in
``/etc/ctf-gameserver``. Individual components are started via systemd
units and are proper ``Type=notify`` services and/or timer units. The
website is special in this regard and runs from your wsgi daemon.

Some settings currently still need code changes. The flag prefix is
hardcoded in the flag module and both checker and submission make
certain assumptions about the IP address layout: the checkermaster
assumes vulnboxes can be reached at ``10.66.$team.2`` and submission
uses the third component of the source IP to determine which team is
submitting the flag.
