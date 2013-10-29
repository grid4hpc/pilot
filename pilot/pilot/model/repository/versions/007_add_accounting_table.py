from sqlalchemy import *
from migrate import *

import datetime

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
)

def upgrade():
    accounting_log_table.create(migrate_engine)

def downgrade():
    accounting_log_table.drop(migrate_engine)
