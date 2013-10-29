from sqlalchemy import *
from migrate import *

import sqlalchemy
from sqlalchemy import Column, Integer, DateTime, Unicode, \
     Binary, ForeignKey, Boolean, MetaData, Table, types
from sqlalchemy.orm import mapper, relation

import datetime, uuid

metadata = MetaData()

jobstates_table = Table(
    'job_states', metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    )

joboperations_table = Table(
    'job_operations', metadata,
    Column('id_key', Integer, primary_key=True),
    Column('op', Unicode(length=32), nullable=False),
    Column('id', Unicode(length=36), nullable=False,
           default=lambda:unicode(uuid.uuid1())),
    Column('created', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('completed', DateTime),
    Column('success', Boolean),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    )

jobs_table = Table(
    'jobs', metadata,
    Column('id', Integer, primary_key=True),
    Column('created', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('modified', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
    Column('expires', DateTime, nullable=False,
           default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=7)),
    Column('owner', Unicode(length=255), nullable=False, index=True),
    Column('definition', Binary),
)

taskstates_table = Table(
    'task_states', metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
           index=True),
    )

tasks_table = Table(
    'tasks', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(length=32), nullable=False),
    Column('created', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('modified', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('definition', Binary),
)

sandboxes_table = Table(
    'sandboxes', metadata,
    Column('id', Integer, primary_key=True),
    Column('type', Unicode(length=1), nullable=False),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
           index=True),
    )

sandbox_files_table = Table(
    'sandbox_files', metadata,
    Column('id', Integer, primary_key=True),
    Column('relname', Unicode(length=256), nullable=False),
    Column('uri', Unicode(length=256), nullable=False),
    Column('sandbox_id', Integer, ForeignKey('sandboxes.id'), nullable=False,
           index=True),
    )

def upgrade():
    tasks_table.create(migrate_engine)
    taskstates_table.create(migrate_engine)
    sandboxes_table.create(migrate_engine)
    sandbox_files_table.create(migrate_engine)

def downgrade():
    taskstates_table.drop(migrate_engine)
    tasks_table.drop(migrate_engine)
    sandboxes_table.drop(migrate_engine)
    sandbox_files_table.drop(migrate_engine)
