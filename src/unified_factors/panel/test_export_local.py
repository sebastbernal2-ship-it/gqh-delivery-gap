"""Safety tests for the private, pinned Snowflake development export."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from . import export_local


class FakeCursor:
    description = [(name,) for name in export_local.EXPECTED_COLUMNS]

    def __init__(self, rows):
        self.rows = rows
        self.query = None

    def execute(self, query):
        self.query = query

    def fetchmany(self, size):
        return self.rows[:size]


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


class ExportLocalTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir='/private/tmp')
        self.output = Path(self.tempdir.name) / 'development.csv'
        self.rows = [('massive_bars', 'a' * 64, '1', 'b' * 64,
                      '2026-10-03T12:00:00Z', '{}')]
        self.cursor = FakeCursor(self.rows)
        self.connection = FakeConnection(self.cursor)
        self.connect = patch.object(export_local, 'connect_kwargs', return_value={})
        self.connect.start()
        self.addCleanup(self.connect.stop)

        snowflake = types.ModuleType('snowflake')
        connector = types.ModuleType('snowflake.connector')
        connector.connect = lambda **kwargs: self.connection
        snowflake.connector = connector
        self.modules = patch.dict(sys.modules, {
            'snowflake': snowflake,
            'snowflake.connector': connector,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_exports_only_pinned_schema_to_private_new_file(self):
        result = export_local.export(self.output, env={})

        self.assertEqual(result['rows'], 1)
        self.assertEqual(result['permissions'], '0600')
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertIn("2024-10-02", self.cursor.query)
        self.assertTrue(self.connection.closed)

    def test_refuses_repository_destination_before_connecting(self):
        with patch.object(export_local, 'connect_kwargs') as connect:
            with self.assertRaisesRegex(ValueError, 'outside the repository'):
                export_local.export(Path(__file__), env={})
        connect.assert_not_called()

    def test_overflow_writes_nothing_and_closes_connection(self):
        self.cursor.rows = self.rows + self.rows
        with self.assertRaisesRegex(ValueError, 'more than 1 rows'):
            export_local.export(self.output, limit=1, env={})

        self.assertFalse(self.output.exists())
        self.assertTrue(self.connection.closed)

    def test_existing_file_is_never_overwritten(self):
        self.output.write_text('preserve me')

        with self.assertRaises(FileExistsError):
            export_local.export(self.output, env={})

        self.assertEqual(self.output.read_text(), 'preserve me')

    def test_rejects_unexpected_result_schema(self):
        self.cursor.description = [('UNEXPECTED',)]

        with self.assertRaisesRegex(ValueError, 'unexpected Snowflake result schema'):
            export_local.export(self.output, env={})

        self.assertFalse(self.output.exists())
        self.assertTrue(self.connection.closed)


if __name__ == '__main__':
    unittest.main()
