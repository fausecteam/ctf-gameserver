"""
Utilities for writing unit tests for CTF Gameserver code.
"""

import os

import django
from django.db import connection
from django.test.testcases import TransactionTestCase
from django.test.utils import setup_databases, teardown_databases


class DatabaseTestCase(TransactionTestCase):
    """
    Base class for test cases which use the Django facilities to provide a temporary test database and
    (database) fixture loading, but test code which does not belong to the web component.
    """

    @classmethod
    def setUpClass(cls):
        """
        Sets up a temporary test database for the whole test case.
        For regular Django tests, this is usually done by Django's test runner.
        """
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctf_gameserver.web.dev_settings')
        django.setup()

        # `interactive=False` causes the test database to be destroyed without asking if it already exists
        cls._old_db_conf = setup_databases(verbosity=1, interactive=False)

        super().setUpClass()

        # Get a fresh raw DB connection with as little of Django's pre-configuration as possible
        cls.connection = connection.get_new_connection(connection.get_connection_params())
        # Ensure SQLite's default isolaton level (without autocommit) is being used
        cls.connection.isolation_level = ''

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        teardown_databases(cls._old_db_conf, verbosity=1)

    @property
    def connection(self):
        return self.__class__.connection
