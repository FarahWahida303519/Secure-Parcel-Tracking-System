"""Delivery Update and Admin Dashboard — Member 3."""
import io
import re
import secrets
import sqlite3
from pathlib import Path
from flask import Blueprint, current_app, request, jsonify, g, send_file
from PIL import Image, UnidentifiedImageError
from shared import db, fail, audit, role, payload, accessible

bp = Blueprint('module3', __name__)

@bp.get('/api/admin')
@role('admin')
def admin():
    return jsonify(users=[dict(r) for r in db().execute('SELECT id,name,email,role,active FROM users ORDER BY id')],counts={r['status']:r['n'] for r in db().execute('SELECT status,count(*) n FROM parcels GROUP BY status')},audit=[dict(r) for r in db().execute('SELECT actor_id,event,created FROM audit ORDER BY id DESC LIMIT 30')])

@bp.post('/api/parcels/<int:parcel_id>/assign')
@role('admin')
def assign(parcel_id):
    rider=payload().get('rider_id')
    if not isinstance(rider,int): return fail('Select a rider.')
    with db():
        if not db().execute('SELECT id FROM users WHERE id=? AND role=? AND active=1',(rider,'rider')).fetchone(): return fail('Select an active rider.')
        cur=db().execute("UPDATE parcels SET rider_id=?,status='Assigned' WHERE id=? AND status='Registered'",(rider,parcel_id))
        if not cur.rowcount: return fail('This parcel cannot be assigned.',409)
        db().execute('INSERT INTO history(parcel_id,status,actor_id) VALUES (?,?,?)',(parcel_id,'Assigned',g.user['id']))
        audit('parcel_assigned',g.user['id'])
    return jsonify(message='Rider assigned.')

@bp.post('/api/parcels/<int:parcel_id>/status')
@role('rider')
def update_status(parcel_id):
    row=accessible(parcel_id)
    if not row: return fail('Parcel not found.',404)
    status=request.form.get('status')
    allowed={'Assigned':['Out for Delivery'],'Out for Delivery':['Delivered','Failed']}
    if status not in allowed.get(row['status'],[]): return fail('This status transition is not allowed.',409)
    filename=None
    if status in ('Delivered','Failed'):
        # M3 SECURITY: decode, verify and re-encode image; private storage, random name.
        upload=request.files.get('proof')
        if not upload or not re.fullmatch(r'[^.\\/]+\.(jpg|jpeg|png)',upload.filename or '',re.I): return fail('Upload one JPG or PNG photo with a simple filename.')
        try:
            raw=upload.read(2*1024*1024+1)
            if len(raw)>2*1024*1024: return fail('Photo must be at most 2 MB.')
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('JPEG','PNG') or image.width*image.height>16000000: return fail('Invalid image or image dimensions too large.')
                image.load()
                filename=secrets.token_hex(24)+'.jpg'
                image.convert('RGB').save(Path(current_app.config['UPLOADS'])/filename,'JPEG',quality=85)
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError): return fail('The file is not a valid JPG or PNG photo.')
    try:
        with db():
            cur=db().execute('UPDATE parcels SET status=?,proof=COALESCE(?,proof) WHERE id=? AND rider_id=? AND status=?',(status,filename,parcel_id,g.user['id'],row['status']))
            if not cur.rowcount:
                if filename: (Path(current_app.config['UPLOADS'])/filename).unlink(missing_ok=True)
                return fail('Parcel changed. Refresh and try again.',409)
            db().execute('INSERT INTO history(parcel_id,status,actor_id) VALUES (?,?,?)',(parcel_id,status,g.user['id']))
            audit('delivery_status_changed',g.user['id'])
    except sqlite3.Error:
        if filename: (Path(current_app.config['UPLOADS'])/filename).unlink(missing_ok=True)
        raise
    return jsonify(message='Delivery updated.')

@bp.get('/api/parcels/<int:parcel_id>/proof')
@role('seller','rider','admin')
def proof(parcel_id):
    row=accessible(parcel_id)
    if not row or not row['proof']: return fail('Photo not found.',404)
    return send_file(Path(current_app.config['UPLOADS'])/row['proof'],mimetype='image/jpeg')
