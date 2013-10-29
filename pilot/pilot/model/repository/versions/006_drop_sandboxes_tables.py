from sqlalchemy import *
from migrate import *
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

sandboxes_table = Table(
    'sandboxes', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('type', Unicode(length=1), nullable=False),
    Column('task_id', Integer, ForeignKey('tasks.id'), nullable=False,
           index=True),
    )

sandbox_files_table = Table(
    'sandbox_files', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('relname', Unicode(length=256), nullable=False),
    Column('uri', Unicode(length=256), nullable=False),
    Column('sandbox_id', Integer, ForeignKey('sandboxes.id'), nullable=False,
           index=True),
    )

def upgrade():
    sandbox_files_table.drop(migrate_engine)
    sandboxes_table.drop(migrate_engine)

def downgrade():
    sandboxes_table.create(migrate_engine)
    sandbox_files.create(migrate_engine)
