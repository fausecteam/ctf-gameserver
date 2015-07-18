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
they do, there will be a way to do that. Expect ++jsonb++.

Protocol
--------

All requests and responses are terminated by a single newline character.

FLAG <tick> <payload>::
  Asks for the valid flag in <tick> containing the <payload>. The
  payload is provided hexencoded. The gameserver answers with the one
  properly signed flag.

RESULT <result>::
  Tells the gameserver it has successfully finished operation. <result>
  is used to communicate the final result back to the gameserver. It
  may be one of the values in the Table below.

.Result codes
[width="50%",options="header",cols="2,10"]
|==========================================================
| <result> | description 
| OK       | Service is running fine and flag was submitted
| TIMEOUT  | Service could not be reached / is offline
| NOTFOUND | The flag we submitted could not be found
|==========================================================


// vim:set ts=4 sw=4 ft=asciidoc noet spell spelllang=en_us:
