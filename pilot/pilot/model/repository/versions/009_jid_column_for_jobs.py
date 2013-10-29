from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

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
    Column('jid', Unicode(length=8), unique=True, nullable=False, index=True)
)

jobs2_table = Table(
    'tmp009', meta.metadata,
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
    Column('jid', Unicode(length=8), unique=True, nullable=True, index=True)
)

def upgrade():
    if migrate_engine.name == 'sqlite':
        if jobs2_table.exists(migrate_engine):
            jobs2_table.drop()
        jobs2_table.create()
        migrate_engine.execute("INSERT INTO tmp009 (id, created, modified, expires, owner, definition, proxy) SELECT id, created, modified, expires, owner, definition, proxy FROM jobs")
        rp = migrate_engine.execute(sa.sql.select([jobs2_table.c.id], from_obj=jobs2_table))
        migrate_engine.echo = True
        for row in rp.fetchall():
            row_id = row['id']
            migrate_engine.execute("UPDATE tmp009 SET jid='%s' WHERE id=%d" % (str(row_id), row_id))
        migrate_engine.echo = False

        jobs_table.drop()
        jobs_table.create()
        migrate_engine.execute("INSERT INTO jobs SELECT * FROM tmp009")
        jobs2_table.drop()
    else:
        if jobs2_table.exists(migrate_engine):
            jobs2_table.drop()
        jobs_table.c.jid.nullable=True
        jobs_table.c.jid.create()
        rp = migrate_engine.execute(sa.sql.select([jobs_table.c.id], from_obj=jobs_table))
        migrate_engine.echo = True
        while True:
            row = rp.fetchone()
            if not row:
                break
            row_id = row['id']
            migrate_engine.execute("UPDATE jobs SET jid='%s' WHERE id=%d" % (str(row_id), row_id))
        migrate_engine.echo = False
        jobs_table.c.jid.nullable=False
        jobs_table.c.jid.alter(nullable=False)

    for idx in jobs_table.indexes:
        try:
            idx.drop(migrate_engine)
            print "dropped index %s" % str(idx)
        except sa.exc.ProgrammingError:
            pass

        try:
            idx.create(migrate_engine)
            print "recreated index %s" % str(idx)
        except sa.exc.ProgrammingError:
            pass

def downgrade():
    if migrate_engine.name == 'sqlite':
        for idx in jobs_table.indexes:
            try:
                idx.drop(migrate_engine)
            except sa.exc.ProgrammingError:
                pass
            except sa.exc.OperationalError:
                pass
    for idx in [idx for idx in jobs_table.indexes if idx.columns[0].name=='jid']:
        jobs_table.indexes.remove(idx)
        
    jobs_table.c.jid.drop()
    if jobs2_table.exists(migrate_engine):
        jobs2_table.drop()
