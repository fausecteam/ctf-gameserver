import os
import locale
import csv

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
        hash_value = salted_hmac(key_salt, value).hexdigest()[::2]

        return '%s-%s' % (ts_b36, hash_value)


email_token_generator = EmailConfirmationTokenGenerator()    # pylint: disable=invalid-name


def get_country_names():
    """
    Returns a list of (English) country names from the OKFN/Core Datasets "List of all countries with their
    2 digit codes" list, which has to be available as a file called "countries.csv" in the same directory as
    this source file.
    """

    csv_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'countries.csv')

    with open(csv_file_name, encoding='utf8') as csv_file:
        csv_reader = csv.reader(csv_file)
        # Skip header line
        next(csv_reader)

        countries = [row[0] for row in csv_reader]
        # Some teams have members in multiple countries
        countries.append('International')

    return sorted(countries, key=locale.strxfrm)
