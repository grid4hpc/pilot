# -*- encoding: utf-8 -*-

from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

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

def upgrade():
    tasks_table.c.runnable.create()
    for idx in tasks_table.indexes:
        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.SQLAlchemyError:
            pass

def downgrade():
    tasks_table.c.runnable.drop()
