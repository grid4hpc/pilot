from sqlalchemy import *
from migrate import *
import migrate.changeset

import datetime

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
)

def upgrade():
    taskstates_table = Table(
        'task_states', meta.metadata,
        Column('id', Integer, primary_key=True),
        Column('s', Unicode(length=32), nullable=False),
        Column('ts', DateTime, nullable=False,
               default=datetime.datetime.utcnow, index=True),
        Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
               index=True),
        Column('info', Unicode(), nullable=True),
        )

    if migrate_engine.name == 'sqlite':
        migrate_engine.execute("CREATE TEMPORARY TABLE `008tmp` AS SELECT * FROM task_states")
        taskstates_table.drop()
        taskstates_table.create()
        migrate_engine.execute("INSERT INTO task_states SELECT * FROM `008tmp`")
        migrate_engine.execute("DROP TABLE `008tmp`")
    else:
        taskstates_table.c.info.alter(type=Unicode())

def downgrade():
    taskstates_table = Table(
        'task_states', meta.metadata,
        Column('id', Integer, primary_key=True),
        Column('s', Unicode(length=32), nullable=False),
        Column('ts', DateTime, nullable=False,
               default=datetime.datetime.utcnow, index=True),
        Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
               index=True),
        Column('info', Unicode(length=255), nullable=True),
        )
    if migrate_engine.name == 'sqlite':
        migrate_engine.execute("CREATE TEMPORARY TABLE `008tmp` AS SELECT * FROM task_states")
        taskstates_table.drop()
        taskstates_table.create()
        migrate_engine.execute("INSERT INTO task_states SELECT * FROM `008tmp`")
        migrate_engine.execute("DROP TABLE `008tmp`")
    else:
        taskstates_table.c.info.alter(type=Unicode(length=255))
