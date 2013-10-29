from sqlalchemy import *
from migrate import *
import migrate.changeset

import datetime, uuid

metadata = MetaData(migrate_engine)

taskstates_table = Table(
    'task_states', metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
           index=True),
    Column('info', Unicode(length=255), nullable=True),
    )

def upgrade():
    taskstates_table.c.info.create()

def downgrade():
    taskstates_table.c.info.drop()
