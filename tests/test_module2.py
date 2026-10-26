"""Security regression tests owned by module2."""
from fixtures import SecurityFixture, connection, io, Image

class Module2Tests(SecurityFixture):
    def test_m2_registration_and_public_privacy(self):
        row=self.parcel().json
        self.assertRegex(row['tracking'],r'^KC-[A-F0-9]{32}$')
        public=self.app.test_client().get('/api/track?number='+row['tracking'])
        self.assertEqual(set(public.json),{'history'})
        self.assertEqual(set(public.json['history'][0]),{'status','created'})
        self.assertNotIn('Fictional',public.text)

    def test_m2_unique_tracking(self):
        self.assertNotEqual(self.parcel().json['tracking'],self.parcel().json['tracking'])

    def test_m2_sql_injection_search(self):
        self.parcel()
        response=self.client.get('/api/parcels',query_string={'q':"' OR 1=1 --"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['parcels'],[])

    def test_m2_foreign_owner_and_proof(self):
        row=self.parcel().json
        self.login('other')
        self.assertEqual(self.client.get('/api/parcels/'+str(row['id'])).status_code,404)
        self.assertEqual(self.client.get('/api/parcels/'+str(row['id'])+'/proof').status_code,404)
        self.assertEqual(self.client.get('/api/parcels').json['parcels'],[])

    def test_m2_invalid_phone(self):
        for phone in ['abc','123','+60<script>','1'*17]:
            with self.subTest(phone=phone): self.assertEqual(self.parcel(phone=phone).status_code,400)

    def test_m2_invalid_weight(self):
        for weight in [-1,0,'abc','NaN','Infinity',51,True,None]:
            with self.subTest(weight=weight): self.assertEqual(self.parcel(weight=weight).status_code,400)

    def test_m2_bounded_input(self):
        for changes in [dict(address='x'*501),dict(address='short'),dict(name='x'*81),dict(name='')]:
            with self.subTest(changes=changes): self.assertEqual(self.parcel(**changes).status_code,400)
        self.assertEqual(self.client.get('/api/parcels?q='+'x'*101).status_code,400)

    def test_m2_xss_is_data_and_renderer_encodes(self):
        attack='<script>alert(1)</script>'
        row=self.parcel(address=attack).json
        self.assertEqual(self.client.get('/api/parcels/'+str(row['id'])).json['parcel']['address'],attack)
        page=self.client.get('/')
        self.assertNotIn(attack,page.text)
        self.assertIn("script-src 'self'",page.headers['Content-Security-Policy'])

    def test_m2_tracking_invalid_formats_and_generic_failure(self):
        messages=[]
        for value in ["' OR 1=1 --",'<script>alert(1)</script>','KC-000001','x'*200,'KC-'+'A'*32]:
            response=self.client.get('/api/track',query_string={'number':value})
            self.assertEqual(response.status_code,404)
            messages.append(response.json['error'])
        self.assertEqual(len(set(messages)),1)

    def test_m2_tracking_rate_limit(self):
        for _ in range(30): self.client.get('/api/track?number=invalid')
        self.assertEqual(self.client.get('/api/track?number=invalid').status_code,429)

    def test_p3_retention(self):
        id=self.parcel().json['id']
        with connection(self.database) as db:
            db.execute("UPDATE parcels SET status='Delivered' WHERE id=?",(id,))
            db.execute("INSERT INTO history(parcel_id,status,actor_id,created) VALUES (?,'Delivered',1,'2020-01-01T00:00:00Z')",(id,))
        result=self.app.test_cli_runner().invoke(args=['anonymize'])
        self.assertEqual(result.exit_code,0)
        row=self.client.get(f'/api/parcels/{id}').json['parcel']
        self.assertEqual(row['name'],'Anonymised'); self.assertEqual(row['phone'],'')
