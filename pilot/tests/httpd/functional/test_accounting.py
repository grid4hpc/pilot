from tests.httpd import *

class TestAccountingController(TestController):

    def test_index(self):
        response = self.app.get(url('accounting_last', records_count=10))
        # XXX: Test response...
