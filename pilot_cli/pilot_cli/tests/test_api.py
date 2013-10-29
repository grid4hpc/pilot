from pilot_cli import api
import datetime
import pytz

from mock import Mock, patch, patch_object

TEST_PILOT = 'https://abbot.homeunix.net:5053/jobs/'

class TestObj(object):
    def __repr__(self):
        return "<TestObj>"

def test_JSONEncoder():
    assert api.json_dumps('hello') == '"hello"'
    assert api.json_dumps(dict(foo='bar', qux=datetime.datetime(2009, 1, 9, 14, 15, 16))) == '{"qux": "2009-01-09T11:15:16.000000Z", "foo": "bar"}'
    assert api.json_dumps(dict(foo='bar', qux=datetime.datetime(2009, 1, 9, 14, 15, 16, tzinfo=pytz.utc))) == '{"qux": "2009-01-09T14:15:16.000000Z", "foo": "bar"}'
    assert api.json_dumps(dict(foo='bar', qux=datetime.datetime(2009, 1, 9, 14, 15, 16, 123))) == '{"qux": "2009-01-09T11:15:16.000123Z", "foo": "bar"}'
    assert api.json_dumps(dict(foo='bar', qux=datetime.datetime(2009, 1, 9, 14, 15, 16, 123, tzinfo=pytz.utc))) == '{"qux": "2009-01-09T14:15:16.000123Z", "foo": "bar"}'
    assert api.json_dumps(dict(x=[dict(foo="bar")])) == '{"x": [{"foo": "bar"}]}'

def test_JSONDecoder():
    data = '{"ts": "2009-01-09T14:15:16Z"}'
    rc = api.json_loads(data)
    assert isinstance(rc['ts'], datetime.datetime)
    assert rc['ts'] == datetime.datetime(2009, 1, 9, 14, 15, 16, tzinfo=pytz.utc)

    data2 = '[ {"ts": "2009-01-09T14:15:16Z", "foo": "bar" }, {"ts": "2009-01-09T14:15:16Z"} ]'
    rc = api.json_loads(data)
    #assert len(rc) == 2
    #assert rc[0]['ts'] == datetime.datetime(2009, 1, 9, 14, 15, 16, tzinfo=pytz.utc)
    #assert rc[0]['foo'] == 'bar'


def test_PilotService_constructor():
    srv = api.PilotService(TEST_PILOT, TestObj())
    assert srv.baseurl == TEST_PILOT
    assert isinstance(srv.options, TestObj)

def test_PilotService_helper_methods():
    srv = api.PilotService(TEST_PILOT, TestObj())
    do_request = Mock()
    srv.do_request = do_request
    srv.get('')
    args, kwargs = do_request.call_args
    req = args[0]
    assert req.get_full_url() == TEST_PILOT
    assert req.get_method() == 'GET'

    srv.delete('1')
    args, kwargs = do_request.call_args
    req = args[0]
    assert req.get_full_url() == TEST_PILOT + '1'
    assert req.get_method() == 'DELETE'
    
    srv.post('2', 'hello')
    args, kwargs = do_request.call_args
    req = args[0]
    assert req.get_full_url() == TEST_PILOT + '2'
    assert req.get_method() == 'POST'
    assert req.headers['Content-length'] == '5'
    assert req.headers['Content-md5'] == 'XUFAKrxLKna5cZ2REBfFkg=='
    
    srv.put('2', 'hello')
    args, kwargs = do_request.call_args
    req = args[0]
    assert req.get_full_url() == TEST_PILOT + '2'
    assert req.get_method() == 'PUT'
    assert req.headers['Content-length'] == '5'
    assert req.headers['Content-md5'] == 'XUFAKrxLKna5cZ2REBfFkg=='
    
