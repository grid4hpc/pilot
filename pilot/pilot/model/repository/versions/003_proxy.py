from sqlalchemy import *
from migrate import *
import migrate.changeset

import datetime, uuid

metadata = MetaData(migrate_engine)

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
    Column('proxy', Binary),
)

def upgrade():
    jobs_table.c.proxy.create()

def downgrade():
    jobs_table.c.proxy.drop()
