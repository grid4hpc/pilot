import logging

from pylons import config
from pylons.controllers.util import abort
from pilot.lib.base import BaseController, render_data, render_json

from pilot import model
from pilot.model.meta import Session
import datetime, pytz, time
from sqlalchemy import and_

log = logging.getLogger(__name__)

def parse_timestamp(timestamp):
    """
    Parse timestamp in format of %Y%m%d%H%M%S[.FFFFFF]

    Returns datetime with UTC timezone.
    """
    start, microseconds = (timestamp.split('.') + ['0'])[:2]
    if len(start) != 14:
        raise ValueError("Timestamp must be in format of YYYYmmddHHMMSS[.FFFFFF] (got %s.%s instead)" % (start, microseconds))
    year, month, day, hour, minute, second, _, _, _ = time.strptime(start, '%Y%m%d%H%M%S')
    micro = int(microseconds)
    result = datetime.datetime(year, month, day, hour, minute, second,
                               micro, pytz.utc)
    return result
    

def render_entries(entries):
    result = []
    for entry in entries:
        record = {'ts': entry.ts,
                  'user_dn': entry.dn,
                  'job_id': entry.job_id,
                  'task_id': entry.task_id,
                  'event': entry.event,
                  'detail': entry.detail,
                  'vo': entry.vo,
                  'info': entry.info}
        result.append(record)

    return render_json(result)

class AccountingController(BaseController):
    # pylint: disable-msg=R0201
    def get_period(self, ts1, ts2):
        ts1 = unicode(ts1)
        ts2 = unicode(ts2)

        if ts1 == u'current':
            return render_data("ts1 cannot be 'current'", code=400)
        
        if ts2 == u'current':
            now = datetime.datetime.utcnow()
            ts2 = now.strftime('%Y%m%d%H%M%S') + '.%06d' % (now.microsecond)

        try:
            start = parse_timestamp(ts1)
        except ValueError, e:
            return render_data("ts1 parsing error: %s" % e, code=400)

        try:
            end = parse_timestamp(ts2)
        except ValueError, e:
            return render_data("ts2 parsing error: %s" % e, code=400)

        # pylint: disable-msg=E1101
        entries = Session.query(model.AccountingLog).filter(
            and_(model.AccountingLog.ts > start,
                model.AccountingLog.ts <= end))

        if self.cert_dn not in config['accounting_access']:
            entries = entries.filter(model.AccountingLog.dn == self.cert_dn)

        entries = entries.order_by(model.AccountingLog.ts)
            
        return render_entries(entries)

    # pylint: disable-msg=R0201
    def get_last(self, records_count):
        entries = Session.query(model.AccountingLog)
        if self.cert_dn not in config['accounting_access']:
            entries = entries.filter(model.AccountingLog.dn == self.cert_dn)

        entries = entries.order_by(model.AccountingLog.ts.desc()) \
                  .limit(records_count)
            
        return render_entries(entries)
