# -*- encoding: utf-8 -*-
from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

from pilot.model import JsonPickleType

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
    Column('definition', JsonPickleType),
    Column('jid', Unicode(length=8), unique=True, nullable=False, index=True),
    Column('deleted', Boolean(), nullable=False, default=False, server_default='0', index=True),
    Column('vo', Unicode(length=64), nullable=True, index=True),
    # текущее состояние задания (id из jobstates_table), не является Foreign key,
    # так как это приведет к циклической зависимости
    Column('state_id', Integer, nullable=True, index=True),
    Column('delegation_id', Integer, ForeignKey('delegations.id'), index=True),
    Column('dirty', Boolean, nullable=False, default=True, server_default='1', index=True),
)

def upgrade():
    jobs_table.c.dirty.create()
    for idx in jobs_table.indexes:
        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.ProgrammingError:
            pass

def downgrade():
    jobs_table.c.dirty.drop()
