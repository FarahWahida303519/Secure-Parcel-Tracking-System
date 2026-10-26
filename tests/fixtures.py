import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import io
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager

@contextmanager
def connection(path):
    db=sqlite3.connect(path)
    try:
        with db:
            yield db
    finally:
        db.close()

from app import create_app, hasher
from PIL import Image
class SecurityFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password=secrets.token_urlsafe(18)
        cls.hash=hasher.hash(cls.password)

    def setUp(self):
        Path(__file__).resolve().parents[1].joinpath('instance').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'instance')
        self.database=str(Path(self.temp.name)/'test.db')
        self.app=create_app({'TESTING':True,'DATABASE':self.database,'UPLOADS':str(Path(self.temp.name)/'proofs')})
        self.client=self.app.test_client()
        with connection(self.database) as db:
            for name,role in [('seller','seller'),('other','seller'),('admin','admin'),('rider','rider'),('other_rider','rider')]:
                db.execute('INSERT INTO users(name,email,password,role) VALUES (?,?,?,?)',(name,name+'@example.test',self.hash,role))
        self.login('seller')

    def tearDown(self): self.temp.cleanup()

    def login(self,name):
        response=self.client.post('/api/login',json={'email':name+'@example.test','password':self.password})
        self.assertEqual(response.status_code,200)
        self.csrf=self.client.get('/api/me').json['csrf']

    def post(self,path,data=None,**kwargs):
        return self.client.post(path,json=data,headers={'X-CSRF-Token':self.csrf},**kwargs)

    def parcel(self,**changes):
        data=dict(name='Fictional Recipient',phone='+60123456789',address='10 Fictional Road, Test City',weight='1.25')
        data.update(changes)
        return self.post('/api/parcels',data)

    def assigned(self):
        row=self.parcel().json
        self.login('admin')
        self.assertEqual(self.post(f"/api/parcels/{row['id']}/assign",{'rider_id':4}).status_code,200)
        self.login('rider')
        return row

    def status(self,id,status,proof=None):
        data={'status':status}
        if proof: data['proof']=proof
        return self.client.post(f'/api/parcels/{id}/status',data=data,headers={'X-CSRF-Token':self.csrf},content_type='multipart/form-data')
