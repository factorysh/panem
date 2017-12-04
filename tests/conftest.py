import time
import sqlalchemy as sa
from panem.app import db

known_errors = (
    'the database system is starting up',
    'communication error',
)


def init_db():
    for i in range(30):
        try:
            db.create_all()
        except (sa.exc.InterfaceError, sa.exc.ProgrammingError) as e:
            if not [m in e.orig.args for m in known_errors]:
                raise
        except sa.exc.OperationalError as e:
            if e.orig.args[0] != 2003:
                raise
        else:
            break
        time.sleep(2)


init_db()
