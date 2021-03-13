General
-------

Database
========

Basically each component needs access to the database. However access
can be (somewhat) restricted.

Checkermaster
^^^^^^^^^^^^^

 - full access on ``scoring_checkerstate``
 - read on ``scoring_gamecontrol``
 - write on ``scoring_statuscheck``
 - write on ``scoring_statuscheck_id_seq``
 - update,read on ``scoring_flag``

Submission
^^^^^^^^^^

 - Read on ``scoring_gamecontrol``
 - Read on ``scoring_flag``
 - Write on ``scoring_capture``
 - Write on ``scoring_capture_id_seq``

Controller / Scoring
^^^^^^^^^^^^^^^^^^^^

 - Read on ``registration_team``
 - Read on ``scoring_service``
 - Write on ``scoring_gamecontrol``
 - Write on ``scoring_flag``
 - Write on ``scoring_flag_id_seq``
 - Owner on ``scoring_scoreboard``

Web
^^^

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
