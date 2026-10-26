"""Security regression tests owned by module3."""
from fixtures import SecurityFixture, connection, io, Image

class Module3Tests(SecurityFixture):
    def test_m3_full_delivery_workflow(self):
        row=self.assigned(); id=row['id']
        self.assertEqual(self.status(id,'Out for Delivery').status_code,200)
        image=io.BytesIO(); Image.new('RGB',(8,8),'green').save(image,format='PNG'); image.seek(0)
        self.assertEqual(self.status(id,'Delivered',(image,'proof.png')).status_code,200)
        proof=self.client.get(f'/api/parcels/{id}/proof'); self.assertEqual(proof.status_code,200); proof.close()
        public=self.client.get('/api/track?number='+row['tracking']).json['history']
        self.assertEqual([h['status'] for h in public],['Registered','Assigned','Out for Delivery','Delivered'])
        self.login('admin')
        self.assertEqual(self.client.get('/api/admin').json['counts']['Delivered'],1)

    def test_m3_foreign_rider_and_invalid_transition(self):
        row=self.assigned(); id=row['id']
        self.assertEqual(self.status(id,'Delivered').status_code,409)
        self.login('other_rider')
        self.assertEqual(self.status(id,'Out for Delivery').status_code,404)
        self.assertEqual(self.post(f'/api/parcels/{id}/assign',{'rider_id':5}).status_code,403)

    def test_m3_malicious_and_oversized_upload(self):
        id=self.assigned()['id']; self.status(id,'Out for Delivery')
        for name,content in [('shell.php.jpg',b'<?php echo 1;'),('fake.jpg',b'not an image'),('big.png',b'x'*(2*1024*1024+1))]:
            with self.subTest(name=name): self.assertEqual(self.status(id,'Delivered',(io.BytesIO(content),name)).status_code,400)
