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
    Column('definition', Binary),
    Column('proxy', Binary),
    Column('jid', Unicode(length=8), unique=True, nullable=False, index=True),
    Column('deleted', Boolean(), nullable=False, default=False, server_default='0', index=True),
    Column('vo', Unicode(length=64), nullable=True, index=True),
)

def upgrade():
    jobs_table.c.vo.create()
    for idx in jobs_table.indexes:
        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.SQLAlchemyError:
            pass

def downgrade():
    jobs_table.c.vo.drop()
