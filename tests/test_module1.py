"""Security regression tests owned by module1."""
from fixtures import SecurityFixture, connection, io, Image

class Module1Tests(SecurityFixture):
    def test_m1_role_and_unauthenticated_access(self):
        self.assertEqual(self.client.get('/api/admin').status_code,403)
        self.login('rider')
        self.assertEqual(self.parcel().status_code,403)
        self.assertEqual(self.app.test_client().get('/api/parcels').status_code,401)

    def test_m1_self_registration_cannot_choose_admin(self):
        response=self.app.test_client().post('/api/register',json={'name':'Test User','email':'new@example.test','password':self.password,'role':'admin'})
        self.assertEqual(response.status_code,201)
        with connection(self.database) as db:
            self.assertEqual(db.execute("SELECT role FROM users WHERE email='new@example.test'").fetchone()[0],'seller')

    def test_m1_login_injection_and_short_password(self):
        self.assertEqual(self.client.post('/api/login',json={'email':"' OR 1=1 --",'password':'bad'}).status_code,401)
        self.assertEqual(self.client.post('/api/register',json={'name':'Test User','email':'new@example.test','password':'short'}).status_code,400)

    def test_m1_logout_revokes_session(self):
        self.assertEqual(self.post('/api/logout').status_code,200)
        self.assertEqual(self.client.get('/api/parcels').status_code,401)

    def test_m1_disable_invalidates_session(self):
        self.login('admin')
        self.assertEqual(self.post('/api/users/1/toggle').status_code,200)
        self.assertEqual(self.client.post('/api/login',json={'email':'seller@example.test','password':self.password}).status_code,401)
