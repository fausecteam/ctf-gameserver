from contextlib import contextmanager


@contextmanager
def transaction_cursor(db_conn):
    """
    Context Manager providing a cursor within a database transaction for any PEP 249-compliant database
    connection (with support for transactions). The transaction will be committed after leaving the context
    and rolled back when an exception occurs in the context.
    Context Managers for the database are not specified by PEP 249 and implemented by some libraries (e.g.
    psycopg2) in ways incompatible to each other.
    """

    # A transaction BEGINs implicitly when the previous one has been finalized
    cursor = db_conn.cursor()

    try:
        yield cursor
    except:
        db_conn.rollback()
        raise

    db_conn.commit()
