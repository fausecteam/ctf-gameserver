CTF Gameserver
==============

This is a gameserver for [attack-defense (IT security) CTFs](https://ctftime.org/ctf-wtf/). It was originally
written for [FAUST CTF 2015](https://www.faustctf.net/2015/), but is designed to be re-usable for other
competitions.

What's included
---------------
The gameserver consists of multiple components. They may be deployed separately of each other as their only
means of communication is a shared database.

* Web: A [Django](https://www.djangoproject.com/)-based web application for team registration and
  scoreboards. It also contains the model files, which define the database structure.
* Controller: Coordinates the progress of the competition, e.g. the current tick and flags to be placed.
* Checker: Offers an interface for checker scripts, which place and retrieve flags and test the status of
  services.
* Submission: Server to submit captured flags to.
* Lib: Some code that is shared between the components.

For deployment instructions and details on the implementations, see the `README`s of the individual
components.

Related projects
----------------
There are several alternatives out there, although none of them could really convince us. Your mileage may
vary at this point.

* ucsb-seclab/ictf-framework from the team behind iCTF, one of the most well-known
  attack-defense CTFs. In addition to a gameserver, it includes utilities for VM creation and network setup.
  We had trouble to get it running and documentation is generally rather rare.
* HackerDom/checksystem is the gameserver powering the RuCTF. The first impression wasn't too bad, but it
  didn't look quite feature-complete to us. However, we didn't really grasp the Perl code, so we might have
  overlooked something.
* isislab/CTFd appears to be de-facto standard for [jeopardy-based CTFs](https://ctftime.org/ctf-wtf/). It
  is, however, not suitable for an attack-defense CTF.

Another factor for the creation of our own system was that we didn't want to build a large CTF on top of a
system which we don't entirely understand.

Design principles
-----------------
The software will probably only be used once a year for severals hours, but it has to work reliably then. It
will hopefully continue to be used by future generations. These requirements led to the incorporation of
some principles:

* Non-complex solutions: Keep the amount of code low and chose the less fancy path. That's why we use the
  built-in Django admin interface instead of writing a custom admin dashboard – it'll be good enough for the
  few people using it.
* Few external dependencies: Of course one shouldn't re-invent the wheel all over again, but every external
  dependency means another moving part. Some libraries you always have to keep up with, others will become
  unmaintained. We therefore focus on few, mature, well-chosen external dependencies. That's why we use a
  plain old Makefile instead of [Bower](http://bower.io/) for JavaScript dependencies and Django's built-in
  PBKDF2 instead of fancy [bcrypt](https://en.wikipedia.org/wiki/Bcrypt) for password hashing.
* Extensive documentation: This should be a no-brainer for any project, although it is easier said than done.
* Re-usability: The gameserver should be adjustable to your needs with some additional lines of code. An
  example for such customizations can be found in the `faustctf-2015` branch of this repository.
* Scalability: We couldn't really estimate the load beforehand, nor could we easily do realistic
  load-testing. That's why the components are loosely coupled and can be run on different machines.

Licensing
---------
The whole gameserver is released under the MIT (expat) license. Contributions are welcome!
