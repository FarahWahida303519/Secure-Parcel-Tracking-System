"""Security regression tests owned by shared."""
from fixtures import SecurityFixture, connection, io, Image

class SharedTests(SecurityFixture):
    def test_shared_csrf_and_origin(self):
        self.assertEqual(self.client.post('/api/parcels',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/parcels',json={},headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.test'}).status_code,403)
