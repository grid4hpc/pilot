from tests.httpd import *
from nose.plugins.attrib import attr

class TestResourceViewController(TestController):
    @attr('slow')
    def test_index(self):
        response = self.app.get(url(controller='resource_view', action='index'))
        # Test response...
