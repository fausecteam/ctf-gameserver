Checker Scripts
===============
Christoph Egger <Christoph.Egger@fau.de>

Considerations
--------------

As the checker will be faced with the full ugliness of foreign input
we can never fully be sure it won't crash oder act stupidly. Therefore
a single checker run will only handle one team and not have direct
access to the flag HMAC secret.

As the flags may contain custom payload the checker script needs a way
to have matching flags generated on demand.

As adding a new flag and retriving the old ones may be similar or
happen in the same run, the checker both submits new flags and tries
to verify whether the service is online.

Purpose & Scope
---------------

Checker scripts must fullfill two purposes: They place flags into the
team's services and check wether the service is fully functional or
not.

There is exactly one checker script per service. Several instances of
the script may be started in parallel. Each such process needs to take
care of exactly one team.

The scripts are given the IP address of their target and the current
tick as arguments (++./checker $tick $ip++) and communicate with the
Gameserver via stdin/out using the protocol specified in the
following.

Ideally checker scripts don't need any persistent state. However if
they do, there will be a way to do that. Expect ++jsonb++. Do _not_
expect to run on the same host for the next tick.

Protocol
--------

All requests and responses are terminated by a single newline character.

FLAG <tick> <payload>::
  Asks for the valid flag in <tick> containing the <payload>. The
  payload field is optional and, if present, contains exactly 8
  hexencoded bytes. The gameserver answers with the one
  properly signed flag.

Success of the checker is comunicated via it's return-code as listed
below. The checker should write any additional information in
free-form to stderr. This output should be in a form suitable to be
displayed to participating teams.

.Return codes
[width="60%",options="header",cols="4,>2,15"]
|==========================================================
| result     | exitcode | description 
| OK         |        0 | Service is running fine and flag was submitted
| TIMEOUT    |        1 | Service could not be reached / is offline
| NOTWORKING |        2 | The service is reachable but does not react properly to requests
| NOTFOUND   |        3 | The flag we submitted could not be found
|==========================================================


// vim:set ts=4 sw=4 ft=asciidoc noet spell spelllang=en_us:
