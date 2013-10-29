from sqlalchemy import *
from migrate import *
import migrate.changeset

import datetime, uuid

metadata = MetaData(migrate_engine)

tasks_table = Table(
    'tasks', metadata,
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
)

def upgrade():
    tasks_table.c.native_id.create()
    tasks_table.c.native_type.create()

def downgrade():
    tasks_table.c.native_id.drop()
    tasks_table.c.native_type.drop()
