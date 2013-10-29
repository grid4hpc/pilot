from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime, itertools

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

jobs_table = Table(
    'jobs', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('created', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('modified', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
    Column('expires', DateTime, nullable=False,
           default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=7)),
    Column('owner', Unicode(length=255), nullable=False, index=True),
    Column('definition', Binary),
    Column('proxy', Binary),
    Column('jid', Unicode(length=8), unique=True, nullable=False, index=True),
    Column('deleted', Boolean(), nullable=False, default=False, server_default='0', index=True),
)

tasks_table = Table(
    'tasks', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('created', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('modified', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('name', Unicode(length=32), nullable=False),
    Column('definition', Binary),
    Column('native_id', Binary, nullable=True),
    Column('native_type', Unicode(length=32), nullable=True),
    Column('deleted', Boolean(), nullable=False, default=False, server_default='0', index=True),
)

def upgrade():
    jobs_table.c.deleted.create()
    tasks_table.c.deleted.create()
    for idx in itertools.chain(jobs_table.indexes, tasks_table.indexes):
        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.SQLAlchemyError:
            pass

def downgrade():
    jobs_table.c.deleted.drop()
    tasks_table.c.deleted.drop()
