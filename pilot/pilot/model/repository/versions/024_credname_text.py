# -*- encoding: utf-8 -*-
from sqlalchemy import *
import sqlalchemy as sa
from migrate import *
import migrate.changeset
import datetime

from pilot.model import JsonPickleType, RSAKeyType, X509ChainType

meta = type('meta', tuple(), {'metadata': MetaData(migrate_engine)})()

def upgrade():
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
    delegations_table.c.credname.drop()
    delegations_table.c.credname.create()

def downgrade():
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

    delegations_table.c.credname.drop()
    delegations_table.c.credname.create()
    
