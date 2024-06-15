CTF Gameserver
==============

FAUST's CTF Gameserver is a gameserver for [attack-defense (IT security) CTFs](https://ctftime.org/ctf-wtf/).
It is used for hosting [FAUST CTF](https://www.faustctf.net), but designed to be re-usable for other
competitions. It is scalable to large online CTFs, battle-tested in many editions of FAUST CTF, and
customizable for other competitions.

Components
----------
The Gameserver consists of multiple components. They may be deployed independently of each other as their
only means of communication is a shared database.

* Web: A [Django](https://www.djangoproject.com/)-based web application for team registration, scoreboards,
  and simple hosting of informational pages. It also contains the model files, which define the database
  structure.
* Controller: Coordinates the progress of the competition, e.g. the current tick and flags to be placed.
* Checker: Place and retrieve flags and test the service status on all teams' Vulnboxes. The Checker Master
  launches Checker Scripts, which are individual to each service.
* Checkerlib: Libraries to assist in developing Checker Scripts. Currently, Python and Go are supported.
* Submission: Server to submit captured flags to.
* VPN Status: Optional helper that collects statistics about network connectivity to teams.

Environment
-----------
CTF Gameserver does **not** include facilities for network infrastructure, VPN setup, and Vulnbox creation.

### Requirements
* Server(s) based on [Debian](https://www.debian.org/) or derivatives
* [PostgreSQL](https://www.postgresql.org/) database
* Web server and WSGI application server for the Web component

### Network
It expects a network, completely local or VPN-based, with the following properties:

* Teams need to be able to reach each other.
* Checkers have to reach the teams.
* Teams should not be able to distinguish between Checker and team traffic, i.e. at least applying a
  masquerading NAT.
* Teams have to reach the Submission server. The Submission server needs to see real source addresses
  (without NAT).
* All Gameserver components need to reach the database. Teams should not be able to talk to the database.
* Both IPv4 and IPv6 are supported. It must be possible to map the teams' network ranges to their
  [team (net) number](architecture.md#team-numbers) based on string patterns. For example, use an addressing
  scheme like `10.66.<team>.0/24`.
* One exception is displaying the latest handshake on the VPN Status History page, which is currently only
  implemented for [WireGuard](https://www.wireguard.com/).

Further Reading
---------------
Some links that contain interesting information for hosting your own CTF:

* A member of the team behind the *Pls, I Want In* CTF wrote about their infrastructure
  [here](https://dev.jameslowther.com/Projects/Pls,-I-Want-In---2024). They used CTF Gameserver and a
  scalable, highly available setup hosted on AWS with Terraform.
* The FAUST CTF infrastructure team gave [a talk on preventing traffic
  fingerprinting](https://www.haproxy.com/user-spotlight-series/preventing-traffic-fingerprinting-in-capture-the-flag-competitions) with iptables and HAProxy
  at HAProxyConf 2022.
