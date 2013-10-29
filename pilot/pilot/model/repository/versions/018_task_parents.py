# -*- encoding: utf-8 -*-

from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime, sys

from pilot.model import JsonPickleType

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

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
    Column('state_id', Integer, nullable=True),
    Column('runnable', Boolean(), nullable=False, default=False, server_default='0', index=True),
)

task_parents_table = Table(
    'task_parents', meta.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), index=True),
    Column('parent_id', Integer, ForeignKey('tasks.id'))
)

def upgrade():
    task_parents_table.create()
    print >> sys.stderr, "==========================================================="
    print >> sys.stderr, "Don't forget to run pilot-spooler --link-tasks"
    print >> sys.stderr, "==========================================================="

def downgrade():
    task_parents_table.drop()
