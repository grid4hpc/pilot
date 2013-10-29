from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

from pilot.model import JsonPickleType

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

accounting_log_table = Table(
    'accounting_log', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('dn', Unicode(length=255), nullable=True, index=True),
    Column('job_id', Unicode(length=40), nullable=True),
    Column('task_id', Unicode(length=32), nullable=True),
    Column('event', Unicode(length=32), nullable=False, index=True),
    Column('detail', Unicode(length=255), nullable=True),
    Column('info', JsonPickleType, nullable=True),
    Column('vo', Unicode(length=64), nullable=True, index=True),
)

def upgrade():
    accounting_log_table.c.info.create()
    accounting_log_table.c.vo.create()
    for idx in accounting_log_table.indexes:
        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.SQLAlchemyError:
            pass

def downgrade():
    accounting_log_table.c.info.drop()
    accounting_log_table.c.vo.drop()
