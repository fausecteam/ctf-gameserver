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
