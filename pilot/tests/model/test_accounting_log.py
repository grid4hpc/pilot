# -*- encoding: utf-8 -*-

from pilot.model import *
from pilot.model.meta import Session

import mock, pdb
from nose.plugins.attrib import attr

import datetime


def last_log():
    return Session.query(AccountingLog).order_by(AccountingLog.ts.desc()).first()


def test_accounting_log_long_entry():
    detail = u"bla blabla bla bla " * 15
    record = AccountingLog(ts=datetime.datetime.now(),
                           dn=u"/foo",
                           job_id=u"bar",
                           event=u"task_aborted",
                           vo=u"qux",
                           detail=detail)
    Session.add(record)
    Session.flush()
    last = last_log()
    assert len(last.detail) <= accounting_log_table.c.detail.type.length
    assert last.detail.endswith("<...>")

    detail = u"a"*accounting_log_table.c.detail.type.length
    record = AccountingLog(ts=datetime.datetime.now(),
                           dn=u"/foo",
                           job_id=u"bar",
                           event=u"task_aborted",
                           vo=u"qux",
                           detail=detail)
    Session.add(record)
    Session.flush()
    last = last_log()
    assert len(last.detail) <= accounting_log_table.c.detail.type.length
    assert not last.detail.endswith("<...>")
