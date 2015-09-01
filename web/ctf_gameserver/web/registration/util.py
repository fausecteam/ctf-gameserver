from django.utils.http import int_to_base36
from django.utils.crypto import salted_hmac
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom variant of django.contrib.auth.tokens.PasswordResetTokenGenerator for usage in email confirmation
    tokens.
    """

    # REVISIT: For Django > 1.8, the parent class has been refactored "to be a bit more extensible"
    def _make_token_with_timestamp(self, user, timestamp):
        """
        This is mostly a copy of the parent class' method.
        The salt has been changed and instead of the password, the user's email address is included in the
        hash.
        """
        ts_b36 = int_to_base36(timestamp)

        key_salt = 'ctf_gameserver.web.registration.util.EmailConfirmationTokenGenerator'

        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0,
                                                                                     tzinfo=None)
        value = (str(user.pk) + user.email + str(login_timestamp) + str(timestamp))
        hash = salted_hmac(key_salt, value).hexdigest()[::2]    # pylint: disable=redefined-builtin

        return '%s-%s' % (ts_b36, hash)

email_token_generator = EmailConfirmationTokenGenerator()    # pylint: disable=invalid-name
