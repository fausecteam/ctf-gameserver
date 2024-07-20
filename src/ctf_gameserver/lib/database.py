from contextlib import contextmanager
import sqlite3


@contextmanager
def transaction_cursor(db_conn, always_rollback=False):
    """
    Context Manager providing a cursor within a database transaction for any PEP 249-compliant database
    connection (with support for transactions). The transaction will be committed after leaving the context
    and rolled back when an exception occurs in the context.
    Context Managers for the database are not specified by PEP 249 and implemented by some libraries (e.g.
    psycopg2) in ways incompatible to each other.

    Args:
        db_conn: A PEP 249-compliant database connection.
        always_rollback: Do never commit transactions, but always roll them back. Useful for testing the
                         required grants (at least with some databases).
    """

    # A transaction BEGINs implicitly when the previous one has been finalized
    cursor = db_conn.cursor()

    if isinstance(cursor, sqlite3.Cursor):
        if sqlite3.threadsafety < 2:
            raise Exception('SQLite must be built with thread safety')

        cursor = _SQLite3Cursor(cursor)

    try:
        yield cursor
    except:    # noqa
        db_conn.rollback()
        raise

    if always_rollback:
        db_conn.rollback()
    else:
        db_conn.commit()


class _SQLite3Cursor:
    """
    Wrapper for sqlite3.Cursor, which translates Psycopg2-style parameter format strings and SQL features
    to constructs understood by SQLite.
    This is quite hacky, but it should only ever be used in tests, as we don't support SQLite in production.
    """

    def __init__(self, orig_cursor):
        self._orig_cursor = orig_cursor

    def __getattribute__(self, name):
        # Prevent endless recursion
        if name == '_orig_cursor':
            return object.__getattribute__(self, name)

        if name == 'execute':
            def sqlite3_execute(_, operation, *args, **kwargs):
                operation = _translate_operation(operation)
                return self._orig_cursor.execute(operation, *args, **kwargs)

            # Turn function into bound method (to be called on an instance)
            # pylint: disable=no-value-for-parameter
            sqlite3_execute_bound = sqlite3_execute.__get__(self, _SQLite3Cursor)
            return sqlite3_execute_bound

        if name == 'executemany':
            def sqlite3_executemany(_, operation, *args, **kwargs):
                operation = _translate_operation(operation)
                return self._orig_cursor.executemany(operation, *args, **kwargs)

            # pylint: disable=no-value-for-parameter
            sqlite3_executemany_bound = sqlite3_executemany.__get__(self, _SQLite3Cursor)
            return sqlite3_executemany_bound

        return self._orig_cursor.__getattribute__(name)


def _translate_operation(operation):
    """
    Translates Psycopg2 features to their SQLite counterparts on a best-effort base.
    """

    # Apart from being a best effort, this also changes the semantics, but SQLite just doesn't support
    # "LOCK TABLE"
    if operation.startswith('LOCK TABLE'):
        return ''

    # The placeholder is always "%s" in Psycopg2, "even if a different placeholder (such as a %d for
    # integers or %f for floats) may look more appropriate"
    operation = operation.replace('%s', '?')
    operation = operation.replace('NOW()', "DATETIME('now')")

    return operation
