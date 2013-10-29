# -*- encoding: utf-8 -*-

import sqlalchemy as sa
from sqlalchemy import Column, Integer, DateTime, Unicode, \
     Binary, ForeignKey, Boolean, MetaData, Table, types, Text, \
     PickleType, String
from sqlalchemy import orm
from sqlalchemy.orm.session import SessionExtension

import copy, datetime, os, uuid, sys

from pilot.model import meta
from pilot.lib import certlib, json

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    ## Reflected tables must be defined and mapped here
    #global reflected_table
    #reflected_table = sa.Table("Reflected", meta.metadata, autoload=True,
    #                           autoload_with=engine)
    #orm.mapper(Reflected, reflected_table)
    #
    meta.Session.configure(bind=engine)
    meta.Session.configure(autoflush=True, autocommit=True,
                           extension=ModifiedUpdaterExtension())
    meta.engine = engine

def srepr(s): return s is None and 'None' or repr(s)

class JsonPickleType(PickleType):
    impl = Binary

    class JsonPickler(object):
        @classmethod
        def dumps(cls, obj, protocol=None):
            return json.dumps(obj, ensure_ascii=True)

        @classmethod
        def loads(cls, str):
            return json.loads(str)

    def __init__(self, mutable=True, comparator=None):
        return PickleType.__init__(self, pickler=self.JsonPickler,
                                   mutable=mutable, comparator=comparator)

class RSAKeyType(sa.types.MutableType, sa.types.TypeDecorator):
    """
    Тип для хранения ключей RSA
    """
    impl = Binary
    def __init__(self, mutable=True, comparator=None):
        self.mutable = mutable
        self.comparator = comparator

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return certlib.rsa_to_der(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return certlib.rsa_load_unencrypted_der(str(value))

    def copy_value(self, value):
        if value is None:
            return None
        if self.mutable:
            return certlib.rsa_load_unencrypted_der(certlib.rsa_to_der(value))
        else:
            return value

    def compare_values(self, x, y):
        if self.comparator:
            return self.comparator(x, y)
        else:
            return x == y

    def is_mutable(self):
        return self.mutable

class X509ChainType(sa.types.MutableType, sa.types.TypeDecorator):
    """
    Тип для хранения цепочек X509_Stack
    """
    impl = Binary
    def __init__(self, mutable=True, comparator=None):
        self.mutable = mutable
        self.comparator = comparator

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.as_der()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return certlib.x509_load_chain_der(str(value))

    def copy_value(self, value):
        if value is None:
            return None
        if self.mutable:
            return certlib.x509_load_chain_der(value.as_der())
        else:
            return value

    def compare_values(self, x, y):
        if self.comparator:
            return self.comparator(x, y)
        else:
            return x == y

    def is_mutable(self):
        return self.mutable

jobstates_table = Table(
    'job_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False, index=True),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), nullable=False,
           index=True),
    Column('info', Unicode(), nullable=True),
    )

joboperations_table = Table(
    'job_operations', meta.metadata,
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

taskstates_table = Table(
    'task_states', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('s', Unicode(length=32), nullable=False, index=True),
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
    Column('definition', JsonPickleType),
    Column('native_id', Binary, nullable=True),
    Column('native_type', Unicode(length=32), nullable=True),
    Column('deleted', Boolean(), nullable=False, default=False, server_default='0', index=True),
    Column('submission_uuid', Unicode(length=36), nullable=True, index=True),
    Column('exit_code', Integer, nullable=True),
    # текущее состояние задачи (id из taskstates_table), не является Foreign key,
    # так как это приведет к циклической зависимости
    Column('state_id', Integer, nullable=True, index=True),
    Column('runnable', Boolean(), nullable=False, default=False, server_default='0', index=True),
    Column('delegation_update_required', Boolean, nullable=False, default=False, server_default='0', index=True),
    Column('delegation_native_id', Binary, nullable=True),
    # произвольные метаданные о задаче.
    # то, что никогда не будет использоваться для выборок.
    Column('meta', JsonPickleType, nullable=True, default={})
)

task_parents_table = Table(
    'task_parents', meta.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), index=True),
    Column('parent_id', Integer, ForeignKey('tasks.id'))
)

accounting_log_table = Table(
    'accounting_log', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('ts', DateTime, nullable=False,
           default=datetime.datetime.utcnow, index=True),
    Column('dn', Unicode(length=255), nullable=True, index=True),
    Column('job_id', Unicode(length=40), nullable=True),
    Column('task_id', Unicode(length=32), nullable=True),
    Column('event', Unicode(length=32), nullable=False, index=True),
    Column('detail', Unicode(length=255), nullable=True),
    Column('info', JsonPickleType, nullable=True),
    Column('vo', Unicode(length=64), nullable=True, index=True),
)

# fqans содержит список FQAN сертификата, разделенные через
# :. Согласно 3.4.1.3 из VOMSACv11.doc, роли и т.д. могут содержать
# только алфавит [a-zA-Z0-9.], поэтому такой выбор разделителя допустим.

delegations_table = Table(
    'delegations', meta.metadata,
    Column('id', Integer, primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column('modified', DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column('expires', DateTime, nullable=False,
           default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=7)),
    Column('owner_hash', String(length=40), nullable=False),
    Column('delegation_id', String(length=64), nullable=False, index=True),
    Column('vo', Unicode(length=64), nullable=False),
    Column('fqans', Text, nullable=False),
    Column('renewable', Boolean, nullable=False, default=False, server_default='0', index=True),
    Column('myproxy_server', String(length=256), nullable=True),
    Column('credname', Text, nullable=True),
    Column('next_expiration', DateTime, nullable=True, index=True),
    Column('key', RSAKeyType, nullable=True, index=True),
    Column('chain', X509ChainType, nullable=True),
    Column('new_key', RSAKeyType, nullable=True),
)

class AccountingLog(object):
    def __init__(self, ts=None, dn=None, job_id=None, task_id=None,
                 event=None, detail=None, vo=None, info=None):
        self.ts = ts
        self.dn = dn
        self.job_id = job_id
        self.task_id = task_id
        self.event = event
        self.detail = detail
        self.vo = vo
        self.info = info

    def __repr__(self):
        return u"<AccountingLog(ts=%s, dn=%s, event=%s, detail=%s, job_id=%s, task_id=%s, vo=%s, info=%s)>" % (
            srepr(self.ts), srepr(self.dn), srepr(self.event),
            srepr(self.detail), srepr(self.job_id), srepr(self.task_id),
            srepr(self.vo), srepr(self.info))

    @orm.validates('detail')
    def truncate_detail(self, key, value):
        max_length = accounting_log_table.c.detail.type.length
        if (value is None) or (len(value) <= max_length):
            return value
        else:
            return value[:max_length-6] + u" <...>"

class JobState(object):
    def __init__(self, s=None, ts=None):
        self.s = unicode(s)
        self.ts = ts

    def __repr__(self):
        return u"<JobState(s=%s, ts='%s')>" % (srepr(self.s), self.ts)

class JobOperation(object):
    def __init__(self, op=None, id=None, created=None, completed=None, success=None):
        self.op = op
        self.id = id
        self.created = created
        self.completed = completed
        self.success = success

    def __repr__(self):
        return u"<JobOperation(op=%s, id='%s', created='%s', completed=%s, success=%s)>" % \
               (srepr(self.op), self.id, self.created,
                srepr(self.completed), srepr(self.success))

class Job(object):
    def __init__(self, expires=None, owner=None, definition=None,
                 states=[], operations=[], delegation=None, jid=None,
                 deleted=None, vo=None):
        self.expires = expires
        self.owner = owner
        self.definition = definition
        self.states = states
        self.operations = operations
        self.delegation = delegation
        self.jid = jid
        self.deleted = deleted
        self.vo = vo

    def __repr__(self):
        return u"<Job(created=%s, modified=%s, expires=%s, owner=%s, definition=%s, states=%s, operations=%s, tasks=%s)>" % \
               (self.created, self.modified, self.expires,
                srepr(self.owner), srepr(self.definition),
                self.states, self.operations, self.tasks)

    def add_state(self, state):
        st = JobState(state)
        self.states.append(st)
        self.dirty = True
        return st

    def add_operation(self, op, id):
        operation = JobOperation(op, id)
        self.operations.append(operation)

    def current_state(self, session):
        return session.query(JobState).filter(JobState.job_id==self.id).order_by(JobState.ts.desc()).first()

    def logname(self):
        return u"/jobs/%s" % self.jid

    @classmethod
    def random_jid(cls):
        return unicode(os.urandom(6).encode('base64') \
                       .strip().replace('+', 'x').replace('/', 'z'))
    
    @classmethod
    def from_dict(cls, definition, delegation, owner, vo, jid=None):
        if jid is None:
            jid = cls.random_jid()

        # XXX: придумать что-нибудь лучше
        job = Job(delegation=delegation, owner=owner, vo=vo, jid=jid)
        job.definition = copy.deepcopy(definition)
        job.add_state(u"new")
        for task_info in job.definition['tasks']:
            task = Task(name = unicode(task_info['id']),
                        definition = task_info.pop('definition'))
            task.add_state(u"new")
            job.tasks.append(task)
        return job

    @property
    def proxy(self):
        """
        Текущая делегация задачи в виде прокси-сертификата
        """
        if self.delegation is None:
            return None
        else:
            return self.delegation.as_proxy()


class TaskState(object):
    def __init__(self, s=None, ts=None):
        self.s = unicode(s)
        self.ts = ts

    def __repr__(self):
        return u"<TaskState(s=%s, ts='%s')>" % (srepr(self.s), self.ts)

class Task(object):
    def __init__(self, name=None, definition=None, states=[], operations=[]):
        self.name = name
        self.definition = definition
        self.states = states
        self.operations = operations

    def __repr__(self):
        return u"<Task(created=%s, modified=%s, job_id=%s, name=%s, definition=%s, states=%s)>" % \
               (self.created, self.modified, srepr(self.job_id),
                srepr(self.name), srepr(self.definition), self.states)

    def add_state(self, state):
        st = TaskState(state)
        self.states.append(st)
        if self.job:
            self.job.dirty = True
        return st

    def logname(self):
        return u"/jobs/%s/%s" % (self.job.jid, self.name)

    def task_group(self):
        u"""
        Возвращает все задачи из группы, которой пренадлежит данная
        (включая саму задачу)
        """
        tasks_group = []
        for group in self.job.definition.get("groups", []):
            if self.name in group:
                tasks_group = group

        if len(tasks_group) == 0:
            return [self]

        return meta.Session.query(Task).filter(
            sa.and_(Task.job_id == self.job.id,
                    Task.name.in_(tasks_group))).all()            


class TaskParent(object):
    def __init__(self, task_id, parent_id):
        self.task_id = task_id
        self.parent_id = parent_id

    def __repr__(self):
        return u"TaskParent(%d, %d)" % (self.task_id, self.parent_id)


class Delegation(object):

    def __init__(self, **kwargs):
        allowed_keys = ('owner_hash', 'delegation_id', 'vo', 'fqans',
                        'renewable', 'myproxy_server', 'credname',
                        'key', 'chain')
        for k, v in kwargs.iteritems():
            if k not in allowed_keys:
                raise ValueError("Invalid argument: %s" % k)
            setattr(self, k, v)

        if self.chain is not None:
            self.update_next_expiration()

    def update_next_expiration(self):
        self.next_expiration = self.chain[0].get_not_after().get_datetime()

    @classmethod
    def from_proxy(cls, proxy):
        key, chain = certlib.load_proxy(proxy)

    @classmethod
    def find_or_create(cls, owner_hash, vo, fqans, proxy=None, key=None, chain=None, delegation_id=None):
        if proxy is not None:
            key, chain = certlib.load_proxy(proxy)
        if (key is None) or (chain is None):
            raise RuntimeError("find_or_create requires proxy or key and chain")
        if delegation_id is None:
            delegation_id = certlib.sha1sum(chain.as_der())
        delegation = meta.Session.query(cls).filter_by(key=key, vo=vo, fqans=fqans, owner_hash=owner_hash).first()
        if delegation is not None:
            return delegation
        delegation = cls(key=key, chain=chain, vo=vo, fqans=fqans,
                         owner_hash=owner_hash,
                         delegation_id=delegation_id)
        meta.Session.add(delegation)
        return delegation

    def __repr__(self):
        return u"Delegation(id=%d, next_expiration='%s')" % (self.id, str(self.next_expiration),)

    def as_proxy(self):
        key = self.key
        chain = self.chain
        proxy_pem = chain[0].as_pem()
        proxy_pem += key.as_pem(None)
        for cert in chain[1:]:
            proxy_pem += cert.as_pem()
        return proxy_pem

    def voms_renew_fqan(self):
        fqans = sorted(self.fqans.split(':'), key=len)
        return fqans[-1]


orm.mapper(AccountingLog, accounting_log_table)
orm.mapper(JobState, jobstates_table)
orm.mapper(JobOperation, joboperations_table)
orm.mapper(TaskState, taskstates_table)
orm.mapper(Task, tasks_table,
       properties = {'states': orm.relation(TaskState, order_by=TaskState.ts, backref="task",
                                            cascade='save-update, merge, delete, delete-orphan'),
                     'state': orm.relation(TaskState, uselist=False,
                                           primaryjoin=tasks_table.c.state_id==taskstates_table.c.id,
                                           foreign_keys=[taskstates_table.c.id]),
                     'parents': orm.relation(Task, secondary=task_parents_table,
                                             primaryjoin = tasks_table.c.id == task_parents_table.c.task_id,
                                             secondaryjoin = tasks_table.c.id == task_parents_table.c.parent_id),
                    })
orm.mapper(TaskParent, task_parents_table,
           primary_key=[task_parents_table.c.task_id, task_parents_table.c.parent_id])
           #properties = {'task': orm.relation(Task, primaryjoin = tasks_table.c.id == task_parents_table.c.task_id),
           #              'parents': orm.relation(Task, primaryjoin = tasks_table.c.id == task_parents_table.c.parent_id),
           #              })
orm.mapper(Delegation, delegations_table)
orm.mapper(Job, jobs_table,
       properties = {'states': orm.relation(JobState, order_by=JobState.ts, backref="job",
                                        cascade='save-update, merge, delete, delete-orphan'),
                     'state': orm.relation(JobState, uselist=False,
                                           primaryjoin=jobs_table.c.state_id==jobstates_table.c.id,
                                           foreign_keys=[jobstates_table.c.id]),
                     'operations': orm.relation(JobOperation, order_by=JobOperation.created,
                                                backref="job",
                                                cascade='save-update, merge, delete, delete-orphan'),
                     'tasks': orm.relation(Task, order_by=Task.id, backref="job",
                                           cascade='save-update, merge, delete, delete-orphan'),
                     'delegation': orm.relation(Delegation, backref="jobs",
                                                cascade="save-update, merge, delete"),
                     })

class ModifiedUpdaterExtension(SessionExtension):
    def before_commit(self, session):
        for obj in session.dirty:
            if 'modified' in dir(obj):
                obj.modified = datetime.datetime.utcnow()
