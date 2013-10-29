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

def upgrade():
    metadata.create_all(migrate_engine)

def downgrade():
    metadata.drop_all(migrate_engine)
