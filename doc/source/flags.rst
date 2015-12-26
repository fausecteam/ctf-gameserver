Flags and Submission
--------------------

Concept
=======

Flags look like ``FAUST_VbDgYwwNs6w3AwAAAABEFEtvyHhdDRuN``. Separated
by ``_`` there is the prefix (``FAUST``) and base64 encoded data with
the following content: ``${timestamp}${teamid}${serviceid}${payload}${hmac}``

As a result, flags can be recreated (as long as no custom payload is
used or the payload is known) at any time. It is possible to check any
flag for validity without looking it up in some database as well as
verifying that it has not expired or is submitted by the owning team.

Submission
==========

Submission is a single-threaded python service accepting flags via a
network socket using non-blocking IO. Several instances can be run
either behind a nginx proxy or just via iptables loadbalancing.

Flag Module
===========

.. autofunction:: ctf_gameserver.lib.flag.generate
.. autofunction:: ctf_gameserver.lib.flag.verify
.. autoexception:: ctf_gameserver.lib.flag.FlagVerificationError
.. autoexception:: ctf_gameserver.lib.flag.InvalidFlagFormat
.. autoexception:: ctf_gameserver.lib.flag.InvalidFlagMAC
.. autoexception:: ctf_gameserver.lib.flag.FlagExpired

Bitstructure of the Data Part
=============================

+-----------+-------------+-------------------------------------------+
| Field     | Size (bits) | Description                               |
+===========+=============+===========================================+
| timestamp | 32          | Flag is valid until timestamp             |
+-----------+-------------+-------------------------------------------+
| teamid    | 8           | Team responsible of protecting this flag  |
+-----------+-------------+-------------------------------------------+
| serviceid | 8           | Service this flag was submitted to        |
+-----------+-------------+-------------------------------------------+
| payload   | 64          | Custom data stored in the Flag, defaults  |
|           |             | to crc32 padded with zeros                |
+-----------+-------------+-------------------------------------------+
| hmac      | 80          | 80 bits from the keccak-100 sponge seeded |
|           |             | with some secret                          |
+-----------+-------------+-------------------------------------------+
