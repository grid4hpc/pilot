# -*- encoding: utf-8 -*-

from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime, sys

from pilot.model.repository import sqlite_drop_indexes

from pilot.model import JsonPickleType, RSAKeyType, X509ChainType

from M2Crypto import BIO, X509, RSA, EVP
from pilot.lib import certlib; certlib.monkey()

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()
Session = sa.orm.scoped_session(sa.orm.sessionmaker())

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
    Column('credname', String(length=64), nullable=True),
    Column('next_expiration', DateTime, nullable=True, index=True),
    Column('key', RSAKeyType, nullable=True, index=True),
    Column('chain', X509ChainType, nullable=True),
    Column('new_key', RSAKeyType, nullable=True),
)

if migrate_engine.name == 'sqlite':
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
        Column('state_id', Integer, nullable=True, index=True),
        Column('delegation_id', Integer, index=True),
    )
else:
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
        Column('state_id', Integer, nullable=True, index=True),
        Column('delegation_id', Integer, ForeignKey('delegations.id'), index=True),
    )

def upgrade():
    delegations_table.create()
    jobs_table.c.delegation_id.create()
    for job_id, proxy_buffer, vo in Session.query(jobs_table.c.id, jobs_table.c.proxy, jobs_table.c.vo):
        if vo is None:
            print "Skipping job", job_id
            continue
        proxy = str(proxy_buffer)
        key, chain = certlib.load_proxy(proxy)

        result = Session.query(delegations_table.c.id).filter(delegations_table.c.key==key).first()
        if not result:
            attrs = { 'owner_hash': certlib.proxy_owner_hash(chain),
                      'vo': unicode(vo),
                      'fqans': u'/%s' % vo,
                      'key': key,
                      'chain': chain,
                      'next_expiration': chain[0].get_not_after().get_datetime(),
                      'delegation_id': certlib.sha1sum(chain.as_der()) }
            Session.execute(delegations_table.insert(attrs))
            result = Session.query(delegations_table.c.id).filter(delegations_table.c.key==key).first()
        else:
            print "reusing delegation %d for job %d" % (result[0], job_id)
        Session.execute(jobs_table.update(jobs_table.c.id==job_id, {'delegation_id': result[0]}))
        Session.flush()
        Session.commit()
    Session.flush()
    Session.commit()
    sqlite_drop_indexes(jobs_table)
    jobs_table.c.proxy.drop()

def downgrade():
    jobs_table.c.proxy.create()
    
    rp = Session.execute(sa.select([jobs_table.c.id, delegations_table.c.key, delegations_table.c.chain],
                                   from_obj=[jobs_table.join(delegations_table, delegations_table.c.id==jobs_table.c.delegation_id)]))
    while True:
        row = rp.fetchone()
        if row is None:
            break
        job_id, key, chain = row
        print "Updating proxy for job", job_id
        proxy_pem = chain[0].as_pem()
        proxy_pem += key.as_pem(None)
        for cert in chain[1:]:
            proxy_pem += cert.as_pem()
        Session.execute(jobs_table.update(jobs_table.c.id==job_id, {'proxy':proxy_pem}))

    Session.flush()
    Session.commit()

    sqlite_drop_indexes(jobs_table)
    if migrate_engine.name == 'sqlite':
        for index in list(jobs_table.indexes):
            for column in index.columns:
                if column.name == 'delegation_id':
                    jobs_table.indexes.remove(index)
                    break
    jobs_table.c.delegation_id.drop()
    delegations_table.drop()
