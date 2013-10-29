# -*- encoding: utf-8 -*-

from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime, sys

from pilot.model import JsonPickleType

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

jobstates_table = Table(
    'job_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False, index=True),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('info', Unicode(), nullable=True),
    )

taskstates_table = Table(
    'task_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False, index=True),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
           index=True),
    Column('info', Unicode(), nullable=True),
    )

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
    Column('vo', Unicode(length=64), nullable=True, index=True),
    # текущее состояние задания (id из jobstates_table), не является Foreign key,
    # так как это приведет к циклической зависимости
    Column('state_id', Integer, nullable=True, index=True),
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
    Column('submission_uuid', Unicode(length=36), nullable=True, index=True),
    Column('exit_code', Integer, nullable=True),
    # текущее состояние задачи (id из taskstates_table), не является Foreign key,
    # так как это приведет к циклической зависимости
    Column('state_id', Integer, nullable=True, index=True),
    Column('runnable', Boolean(), nullable=False, default=False, server_default='0', index=True),
)

def upgrade():
    for table in (jobstates_table, taskstates_table, tasks_table, jobs_table):
        print >> sys.stderr, "Creating index for table %s" % table.name
        for index in table.indexes:
            if index.columns[0].name in (u"s", u"state_id"):
                index.create()
        print >> sys.stderr, "Running ANALYZE on table %s" % table.name
        migrate_engine.execute(sa.schema.DDL("ANALYZE %s;" % table.name))

def downgrade():
    for table in (jobstates_table, taskstates_table, tasks_table, jobs_table):
        for index in table.indexes:
            if index.columns[0].name in (u"s", u"state_id"):
                index.drop()
