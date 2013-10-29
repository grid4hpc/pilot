# -*- encoding: utf-8 -*-

import sqlalchemy as sa
from migrate import *

def sqlite_drop_indexes(*tables):
    if migrate_engine.name != 'sqlite':
        return
    
    for table in tables:
        print "SQLite workaround: dropping indexes for table", table.name
        for idx in table.indexes:
            try:
                idx.drop(migrate_engine)
                print "dropped index", idx.name
            except (sa.exc.OperationalError, sa.exc.ProgrammingError):
                pass
        
