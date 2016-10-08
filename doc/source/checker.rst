Checkers
--------

Purpose & Scope
===============

Checker scripts must fullfill two purposes: They place flags into the
team's services and check wether the service is fully functional or
not. They check for presence of all flags that are still valid to
submit.

There is exactly one checker script per service. Several instances of
the script may be started in parallel. Each such process needs to take
care of exactly one team.

Currently checkers are expected to be implemented as python modules
with one class inheriting
:py:class:`ctf_gameserver.checker.BaseChecker`. The :py:class:`BaseChecker`
inherits from the :py:class:`AbstractChecker` documented below.

For service authors to locally test their checker a ``testrunner`` is
provided which can be called like this::

  mytemp=`mktemp -d`
  for i in {0..10}
  do
    ./testrunner.py --first 1437258032 --backend $mytemp --tick $i --ip $someip --team 1 --service 1 dummy:DummyChecker
  done

During the contest, checks are run by the ``checkermaster`` and
``checkerslave`` pair where the ``checkerslave`` starts the
checkermodule and comunicates with the ``checkermaster`` via
stdin/stdout. The ``checkermaster`` is responsible for monitoring the
individual checker processes recording their result and starting new
ones as needed.

Contest services
================

The checker ships with a ``checkermaster@.service`` file. The checker
config files most be stored in ``/etc/ctf-gameserver`` and can then be
used with the ``checkermaster@dummy`` services. The python module
should go to the ``checker/`` subdirectory. The supplied setup has the
checkermaster logging to systemd's journal. Additionally to the full
journal for the individual checkermaster units (one per service to
check) you can also access the checkerscript's logging from the journal::

  journalctl -u ctf-checkermaster@someservice.service SYSLOG_IDENTIFIER=team023-tick042

API Baseclass
=============

.. autoclass:: ctf_gameserver.checker.abstract.AbstractChecker
   :members:
