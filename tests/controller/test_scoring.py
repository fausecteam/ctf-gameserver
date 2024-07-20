import csv
import os

from ctf_gameserver.controller import scoring
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase


class ScoringTest(DatabaseTestCase):

    fixtures = ['tests/controller/fixtures/scoring.json.xz']

    def test_scoreboard(self):
        def r(val):
            return round(val, 6)

        ref_path = os.path.join(os.path.dirname(__file__), 'scoring_reference.csv')
        with open(ref_path, newline='', encoding='ascii') as ref_file:
            ref_reader = csv.reader(ref_file, quoting=csv.QUOTE_NONNUMERIC)
            ref_values = [(int(v[0]), int(v[1]), r(v[2]), r(v[3]), r(v[4]), r(v[5])) for v in ref_reader]

        scoring.calculate_scoreboard(self.connection)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT team_id, service_id, attack, defense, sla, total'
                           '    FROM scoring_scoreboard ORDER BY team_id, service_id')
            values = [(v[0], v[1], r(v[2]), r(v[3]), r(v[4]), r(v[5])) for v in cursor.fetchall()]

        self.assertEqual(values, ref_values)


class EmptyScoringTest(DatabaseTestCase):
    """
    Make sure that scoreboard calculation works on an empty database.
    """

    def test_scoreboard(self):
        scoring.calculate_scoreboard(self.connection)
