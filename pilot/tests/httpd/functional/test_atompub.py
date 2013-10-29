from tests.httpd import *

class TestAtomPubController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='atompub', action='index'))
        # Test response...
