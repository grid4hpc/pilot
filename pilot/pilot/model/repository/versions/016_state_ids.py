# -*- encoding: utf-8 -*-

from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime, sys

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
    # текущее состояние задания (id из jobstates_table), не является Foreign key,
    # так как это приведет к циклической зависимости
    Column('state_id', Integer, nullable=True),
)

jobstates_table = Table(
    'job_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('info', Unicode(), nullable=True),
    )

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
)


def postgres_upgrade_triggers():
    try:
        migrate_engine.execute(sa.schema.DDL("""
            CREATE LANGUAGE plpgsql;
        """))
    except sa.exc.ProgrammingError, exc:
        # если язык уже есть - ничго страшного
        pass

    migrate_engine.execute(sa.schema.DDL("""
        CREATE FUNCTION tr_job_state_added() RETURNS trigger AS $tr_job_state_added$
            BEGIN
                UPDATE jobs SET state_id = NEW.id WHERE id = NEW.job_id;
                RETURN NEW;
            END;
        $tr_job_state_added$ LANGUAGE plpgsql;    
        CREATE TRIGGER tr_job_state_added AFTER INSERT ON job_states FOR EACH ROW EXECUTE PROCEDURE tr_job_state_added();
        CREATE FUNCTION tr_task_state_added() RETURNS trigger AS $tr_task_state_added$
            BEGIN
                UPDATE tasks SET state_id = NEW.id WHERE id = NEW.task_id;
                RETURN NEW;
            END;
        $tr_task_state_added$ LANGUAGE plpgsql;    
        CREATE TRIGGER tr_task_state_added AFTER INSERT ON task_states FOR EACH ROW EXECUTE PROCEDURE tr_task_state_added();
    """))

def postgres_downgrade_triggers():
    migrate_engine.execute(sa.schema.DDL("""
        DROP TRIGGER tr_job_state_added ON job_states;
        DROP FUNCTION tr_job_state_added();
        DROP TRIGGER tr_task_state_added ON task_states;
        DROP FUNCTION tr_task_state_added();
    """))

def sqlite_upgrade_triggers():
    migrate_engine.execute(sa.schema.DDL("""
        CREATE TRIGGER tr_job_state_added AFTER INSERT ON job_states FOR EACH ROW
            BEGIN
                UPDATE jobs SET state_id = new.id WHERE id = new.job_id;
            END;
    """))
    migrate_engine.execute(sa.schema.DDL("""
        CREATE TRIGGER tr_task_state_added AFTER INSERT ON task_states FOR EACH ROW
            BEGIN
                UPDATE tasks SET state_id = new.id WHERE id = new.task_id;
            END;
    """))
                           
def sqlite_downgrade_triggers():
    migrate_engine.execute(sa.schema.DDL("""
        DROP TRIGGER tr_job_state_added;
    """))
    migrate_engine.execute(sa.schema.DDL("""
        DROP TRIGGER tr_task_state_added;
    """))


update_triggers = {
    'sqlite': (sqlite_upgrade_triggers, sqlite_downgrade_triggers),
    'postgres': (postgres_upgrade_triggers, postgres_downgrade_triggers),
    }

def upgrade():
    if migrate_engine.name not in update_triggers:
        raise sa.exc.ProgrammingError("Sorry, database %s is not supported" % migrate_engine.name)
    t_upgrade, t_downgrade = update_triggers[migrate_engine.name]
    jobs_table.c.state_id.create()
    tasks_table.c.state_id.create()
    print "Creating triggers"
    t_upgrade()

    print "Updating jobs"
    session = sa.orm.sessionmaker(bind=migrate_engine)()
    counter = 0
    for (job_id,) in session.query(jobs_table.c.id):
        (jobstate_id,) = session.query(jobstates_table.c.id).filter(
            jobstates_table.c.job_id==job_id).order_by(
            sa.desc(jobstates_table.c.ts)).first()
        session.execute(jobs_table.update().where(jobs_table.c.id==job_id).values(state_id=jobstate_id))
        counter += 1
        if counter % 20 == 0 and counter > 0:
            sys.stderr.write('.')
            sys.stderr.flush()
    session.commit()

    print "Updating tasks"
    counter = 0
    for (task_id,) in session.query(tasks_table.c.id):
        (taskstate_id,) = session.query(taskstates_table.c.id).filter(
            taskstates_table.c.task_id==task_id).order_by(
            sa.desc(taskstates_table.c.ts)).first()
        session.execute(tasks_table.update().where(tasks_table.c.id==task_id).values(state_id=taskstate_id))
        counter += 1
        if counter % 20 == 0 and counter > 0:
            sys.stderr.write('.')
            sys.stderr.flush()
    session.commit()

def downgrade():
    if migrate_engine.name not in update_triggers:
        raise sa.exc.ProgrammingError("Sorry, database %s is not supported" % migrate_engine.name)
    if migrate_engine.name == 'sqlite':
        for idx in jobs_table.indexes:
            try:
                idx.drop(migrate_engine)
            except sa.exc.ProgrammingError:
                pass
            except sa.exc.OperationalError:
                pass
    t_upgrade, t_downgrade = update_triggers[migrate_engine.name]
    t_downgrade()
    jobs_table.c.state_id.drop()
    tasks_table.c.state_id.drop()
