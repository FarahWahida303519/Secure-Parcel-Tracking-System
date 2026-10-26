"""Real page rendering, role boundaries and module asset isolation."""
from fixtures import SecurityFixture

# Reuse fixtures/helpers without rerunning inherited test methods.
class PageTests(SecurityFixture):
    pass

def public_pages(self):
    anonymous=self.app.test_client()
    for path in ['/', '/login', '/register', '/track']:
        with self.subTest(path=path):
            response=anonymous.get(path)
            self.assertEqual(response.status_code,200)
            self.assertIn('<!doctype html>',response.text)
    for path in ['/parcels','/parcels/new','/account','/users','/deliveries','/dashboard']:
        with self.subTest(path=path):self.assertEqual(anonymous.get(path).status_code,302)

def module2_pages(self):
    attack='<script>alert(1)</script>'
    parcel=self.parcel(name=attack,address=attack).json
    for path in ['/parcels','/parcels/new',f"/parcels/{parcel['id']}",'/track']:
        with self.subTest(path=path):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertIn('/static/js/module2.js',response.text)
            self.assertIn('/static/css/module2.css',response.text)
            self.assertNotIn('/static/js/module1.js',response.text)
            self.assertNotIn('/static/js/module3.js',response.text)
            self.assertNotIn(attack,response.text)
    detail=self.client.get(f"/parcels/{parcel['id']}")
    self.assertIn('&lt;script&gt;',detail.text)
    self.assertEqual(self.client.get('/dashboard').status_code,403)
    self.assertEqual(self.client.get('/deliveries').status_code,403)
    self.login('other')
    self.assertEqual(self.client.get(f"/parcels/{parcel['id']}").status_code,404)

def friend_pages(self):
    parcel=self.parcel().json
    self.login('admin')
    for path in ['/account','/users','/dashboard','/deliveries',f"/deliveries/{parcel['id']}"]:
        with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
    self.assertEqual(self.client.get('/parcels/new').status_code,403)
    self.post(f"/api/parcels/{parcel['id']}/assign",{'rider_id':4})
    self.login('rider')
    self.assertEqual(self.client.get(f"/deliveries/{parcel['id']}").status_code,200)
    self.assertEqual(self.client.get('/users').status_code,403)
    self.assertEqual(self.client.get('/dashboard').status_code,403)
    self.login('other_rider')
    self.assertEqual(self.client.get(f"/deliveries/{parcel['id']}").status_code,404)

def assets(self):
    for module in ['shared','module1','module2','module3']:
        for folder,extension in [('css','css'),('js','js')]:
            response=self.client.get(f'/static/{folder}/{module}.{extension}')
            self.assertEqual(response.status_code,200)
            response.close()

PageTests.test_public_pages=public_pages
PageTests.test_module2_html_pages_and_escaping=module2_pages
PageTests.test_friend_pages_and_access=friend_pages
PageTests.test_module_assets=assets
