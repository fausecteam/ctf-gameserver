CTF Gameserver
==============

This is a Gameserver for [attack-defense (IT security) CTFs](https://ctftime.org/ctf-wtf/). It is used for
hosting [FAUST CTF](https://www.faustctf.net), but designed to be re-usable for other competitions. It is
scalable to large online CTFs, battle-tested in many editions of FAUST CTF, and customizable for other
competitions.

For documentation on architecture, installation, etc., head to [ctf-gameserver.org](https://ctf-gameserver.org/).

What's Included
---------------
The Gameserver consists of multiple components:

* Web: A [Django](https://www.djangoproject.com/)-based web application for team registration, scoreboards,
  and simple hosting of informational pages. It also contains the model files, which define the database
  structure.
* Controller: Coordinates the progress of the competition, e.g. the current tick and flags to be placed.
* Checker: Place and retrieve flags and test the service status on all teams' Vulnboxes. The Checker Master
  launches Checker Scripts, which are individual to each service.
* Checkerlib: Libraries to assist in developing Checker Scripts. Currently, Python and Go are supported.
* Submission: Server to submit captured flags to.
* VPN Status: Optional helper that collects statistics about network connectivity to teams.

Related Projects
----------------
There are several alternatives out there, although none of them could really convince us when we started the
project in 2015. Your mileage may vary.

* [ictf-framework](https://github.com/shellphish/ictf-framework) from the team behind iCTF, one of the most
  well-known attack-defense CTFs. In addition to a gameserver, it includes utilities for VM creation and
  network setup. We had trouble to get it running and documentation is generally rather scarce.
* [HackerDom checksystem](https://github.com/HackerDom/checksystem) is the Gameserver powering RuCTF. The
  first impression wasn't too bad, but it didn't look quite feature-complete to us. However, we didn't really
  grasp the Perl code, so we might have overlooked something.
* [saarctf-gameserver](https://github.com/MarkusBauer/saarctf-gameserver) from our friends at saarsec is
  younger than our Gameserver. It contains a nice scoreboard and infrastructure for VPN/network setup.
* [EnoEngine](https://github.com/enowars/EnoEngine) by our other friends at ENOFLAG is also younger than
  our solution.
* [CTFd](https://ctfd.io/) is the de-facto standard for [jeopardy-based CTFs](https://ctftime.org/ctf-wtf/).
  It is, however, not suitable for an attack-defense CTF.

Another factor for the creation of our own system was that we didn't want to build a large CTF on top of a
system which we don't entirely understand.

Development
-----------
For a local development environment, set up a [Python venv](https://docs.python.org/3/library/venv.html) or
use our [dev container](https://code.visualstudio.com/docs/devcontainers/containers) from
`.devcontainer.json`.

Then, run `make dev`. Tests can be executed through `make test` and a development instance of the Web
component can be launched with `make run_web`.

We always aim to keep our Python dependencies compatible with the versions packaged in Debian stable.
Debian-based distributions are our primary target, but the Python code should generally be
platform-independent.

Security
--------
Should you encounter any security vulnerabilities in the Gameserver, please report them to us privately.
Use GitHub vulnerability reporting or contact Felix Dreissig or Simon Ruderich directly.

Copyright
---------
The Gameserver was initially created by Christoph Egger and Felix Dreissig. It is currently maintained by
Felix Dreissig and Simon Ruderich with contributions from others.

It is released under the ISC License.
