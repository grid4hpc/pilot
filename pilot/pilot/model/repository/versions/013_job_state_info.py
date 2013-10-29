from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

jobstates_table = Table(
    'job_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('info', Unicode(), nullable=True),
    )

def upgrade():
    jobstates_table.c.info.create()

def downgrade():
    jobstates_table.c.info.drop()
