import base64
import binascii
import datetime
import hashlib
from hmac import compare_digest
import struct

# Length of the MAC (in bytes)
MAC_LEN = 10
# expiration_timestamp + flag.id + protecting_team.net_no
DATA_LEN = 8 + 4 + 2
# Static string with which flags get XOR-ed to make them look more random (just for the looks)
XOR_STRING = b'CTF-GAMESERVER'


def generate(expiration_time, flag_id, team_net_no, secret, prefix='FLAG_'):
    """
    Generates a flag for the given arguments, i.e. the MAC-protected string that gets placed in services and
    captured by teams. This is deterministic and should always return the same result for the same arguments.

    Args:
        expiration_time: Datetime object (preferably timezone-aware) at which the flag expires
        flag_id: ID (primary key) of the flag's associated database entry
        team_net_no: Net number of the team protecting this flag
        secret: Secret used for the MAC
        prefix: String to prepend to the generated flag
    """

    if flag_id < 0 or flag_id > 2**32 - 1:
        raise ValueError('Flag ID must fit in unsigned 32 bits')
    if team_net_no < 0 or team_net_no > 2**16 - 1:
        raise ValueError('Team net number must fit in unsigned 16 bits')

    protected_data = struct.pack('! Q I H', int(expiration_time.timestamp()), flag_id, team_net_no)
    protected_data = bytes([c ^ d for c, d in zip(protected_data, XOR_STRING)])
    mac = _gen_mac(secret, protected_data)

    return prefix + base64.b64encode(protected_data + mac).decode('ascii')


def verify(flag, secret, prefix='FLAG_'):
    """
    Verifies flag validity and returns data from the flag.
    Will raise an appropriate exception if verification fails.

    Args:
        flag: MAC-protected flag string
        secret: Secret used for the MAC
        prefix: String to prepend to the generated flag

    Returns:
        Data from the flag as a tuple of (flag_id, team_net_no)
    """

    if not flag.startswith(prefix):
        raise InvalidFlagFormat()

    try:
        raw_flag = base64.b64decode(flag[len(prefix):])
    except (ValueError, binascii.Error):
        raise InvalidFlagFormat() from None

    try:
        protected_data, flag_mac = raw_flag[:DATA_LEN], raw_flag[DATA_LEN:]
    except IndexError:
        raise InvalidFlagFormat() from None

    mac = _gen_mac(secret, protected_data)
    if not compare_digest(mac, flag_mac):
        raise InvalidFlagMAC()

    protected_data = bytes([c ^ d for c, d in zip(protected_data, XOR_STRING)])
    expiration_timestamp, flag_id, team_net_no = struct.unpack('! Q I H', protected_data)
    expiration_time = datetime.datetime.fromtimestamp(expiration_timestamp, datetime.timezone.utc)
    if expiration_time < _now():
        raise FlagExpired(expiration_time)

    return (flag_id, team_net_no)


def _gen_mac(secret, protected_data):

    # Keccak does not need an HMAC construction, the secret can simply be prepended
    sha3 = hashlib.sha3_256()
    sha3.update(secret)
    sha3.update(protected_data)
    return sha3.digest()[:MAC_LEN]


def _now():
    """
    Wrapper around datetime.datetime.now() to enable mocking in test cases.
    """

    return datetime.datetime.now(datetime.timezone.utc)


class FlagVerificationError(Exception):
    """
    Base class for all Flag Exceptions.
    """


class InvalidFlagFormat(FlagVerificationError):
    """
    Flag does not match the expected format.
    """


class InvalidFlagMAC(FlagVerificationError):
    """
    MAC does not match with configured secret.
    """


class FlagExpired(FlagVerificationError):
    """
    Flag is already expired.
    """

    def __init__(self, expiration_time):
        super().__init__(f'Flag expired since {expiration_time}')
        self.expiration_time = expiration_time
