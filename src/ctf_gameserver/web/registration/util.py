import os
import locale
import csv

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.template import loader

import ctf_gameserver.web.scoring.models as scoring_models


def send_confirmation_mail(user, request):
    """
    Sends an email containing the email address confirmation link to the given user. As it requires a User
    instance, it should only be called after the User object has initially been saved.

    Args:
        request: An HttpRequest from which this function is being called
    """

    email_token_generator = EmailConfirmationTokenGenerator()
    competition_name = scoring_models.GameControl.get_instance().competition_name

    context = {
        'competition_name': competition_name,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': get_current_site(request),
        'user': user.pk,
        'token': email_token_generator.make_token(user)
    }
    message = loader.render_to_string('confirmation_mail.txt', context)

    send_mail(competition_name+' email confirmation', message, settings.DEFAULT_FROM_EMAIL, [user.email])


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom variant of django.contrib.auth.tokens.PasswordResetTokenGenerator for usage in email confirmation
    tokens.
    """

    key_salt = 'ctf_gameserver.web.registration.util.EmailConfirmationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        """
        This is mostly a copy of the parent class' method.
        Instead of the password, the user's email address is included in the hash.
        """
        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0,
                                                                                     tzinfo=None)
        return str(user.pk) + user.email + str(login_timestamp) + str(timestamp)


def get_country_names():
    """
    Returns a list of (English) country names from the OKFN/Core Datasets "List of all countries with their
    2 digit codes" list, which has to be available as a file called "countries.csv" in the same directory as
    this source file.
    """

    csv_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'countries.csv')

    with open(csv_file_name, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        # Skip header line
        next(csv_reader)

        countries = [row[0] for row in csv_reader]
        # Some teams have members in multiple countries
        countries.append('International')

    return sorted(countries, key=locale.strxfrm)
