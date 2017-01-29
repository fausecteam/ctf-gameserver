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
    ./ctf-testrunner --first 1437258032 --backend $mytemp --tick $i --ip $someip --team 1 --service 1 dummy:DummyChecker
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

Writing a checker
=================

Having robust checker scripts is essential for a fun
competition. Checkerscripts will encounter different kinds of half
broken services, slow network, unreachable hosts and lots of other
things. The checkerscript should therefore set reasonable timeouts for
all interactions and handle all exceptions for which it can properly
assign a return value. If an unexpected (and therefore unhandled)
exception occurs, the :py:class:`BaseChecker` will create an
appropriate logentry and not write any result into the database.

The baseclass :py:class:`BaseChecker` provides a :py:mod:`logging`
logger which is set up properly to create well integrated logs with
all the relevant metainformation. All checkers should use it instead
of the global functions from the :py:mod:`logging` module.

Checkers need to be able to recover from partial data loss on the
vulnboxes. They should not create login credentials on first run and
continue using them forever -- doing so would make it trivial to
distinguish the gameserver and will make the checker fail for the rest
of the competition if a vulnbox has been reset in the middle of the
game.

API Baseclass
=============

.. autoclass:: ctf_gameserver.checker.abstract.AbstractChecker
   :members:
