"""Parcel Registration and Public Tracking — YOUR MODULE."""
import re
import math
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from flask import Blueprint, current_app, request, jsonify, g
from shared import db, fail, audit, limited, role, payload, text, accessible

bp = Blueprint('module2', __name__, cli_group=None)

@bp.get('/api/parcels')
@role('seller','rider','admin')
def parcels():
    # M2 SECURITY: bound parameters keep SQL injection in search inert.
    query=request.args.get('q','')
    if len(query)>100: return fail('Search must be 100 characters or fewer.')
    sql='SELECT * FROM parcels WHERE 1=1'; args=[]
    if g.user['role']=='seller': sql+=' AND seller_id=?'; args.append(g.user['id'])
    if g.user['role']=='rider': sql+=' AND rider_id=?'; args.append(g.user['id'])
    sql+=' AND (tracking LIKE ? ESCAPE \'!\' OR name LIKE ? ESCAPE \'!\') ORDER BY id DESC LIMIT 200'
    escaped=query.replace('!','!!').replace('%','!%').replace('_','!_')
    args += ['%'+escaped+'%']*2
    return jsonify(parcels=[dict(r) for r in db().execute(sql,args)])

@bp.post('/api/parcels')
@role('seller')
def create_parcel():
    data=payload()
    # M2 SECURITY: server validation is authoritative; HTML validation is UX only.
    if not text(data.get('name'),80,2): return fail('Recipient name must be 2–80 characters.')
    if not isinstance(data.get('phone'),str) or not re.fullmatch(r'\+?\d{9,15}',data['phone']): return fail('Phone must contain 9–15 digits, optionally starting with +.')
    if not text(data.get('address'),500,10): return fail('Address must be 10–500 characters.')
    try:
        if isinstance(data.get('weight'),bool): raise ValueError()
        weight=float(data.get('weight',''))
        if not math.isfinite(weight) or not 0<weight<=50: raise ValueError()
    except (ValueError,TypeError): return fail('Weight must be a number greater than 0 and at most 50 kg.')
    # M2 SECURITY: 128 random bits + database uniqueness; never sequential IDs.
    for _ in range(3):
        tracking='KC-'+secrets.token_hex(16).upper()
        try:
            with db():
                cur=db().execute('INSERT INTO parcels(tracking,seller_id,name,phone,address,weight) VALUES (?,?,?,?,?,?)',(tracking,g.user['id'],data['name'].strip(),data['phone'],data['address'].strip(),weight))
                db().execute('INSERT INTO history(parcel_id,status,actor_id) VALUES (?,?,?)',(cur.lastrowid,'Registered',g.user['id']))
                audit('parcel_registered',g.user['id'])
            return jsonify(message='Parcel registered.',tracking=tracking,id=cur.lastrowid),201
        except sqlite3.IntegrityError:
            continue
    return fail('Unable to register the parcel. Try again.',503)

@bp.get('/api/parcels/<int:parcel_id>')
@role('seller','rider','admin')
def detail(parcel_id):
    row=accessible(parcel_id)
    if not row: return fail('Parcel not found.',404)
    return jsonify(parcel=dict(row),history=[dict(r) for r in db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(parcel_id,))])

@bp.get('/api/track')
def track():
    # M2 SECURITY P3: allowlist public fields; no recipient or actor information.
    if limited('tracking',30,60): return fail('Too many lookups. Please wait one minute.',429)
    tracking=request.args.get('number','').upper()
    if not re.fullmatch(r'KC-[A-F0-9]{32}',tracking): return fail('No parcel found. Check your tracking number.',404)
    row=db().execute('SELECT id FROM parcels WHERE tracking=?',(tracking,)).fetchone()
    if not row: return fail('No parcel found. Check your tracking number.',404)
    return jsonify(history=[dict(r) for r in db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(row['id'],))])

@bp.cli.command('anonymize')
def anonymize():
    # P3 retention: run daily via OS scheduler; keep status-only history.
    cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows=db().execute("SELECT p.id,p.proof FROM parcels p WHERE p.status='Delivered' AND EXISTS(SELECT 1 FROM history h WHERE h.parcel_id=p.id AND h.status='Delivered' AND h.created<?)",(cutoff,)).fetchall()
    with db():
        for row in rows:
            if row['proof']: (Path(current_app.config['UPLOADS'])/row['proof']).unlink(missing_ok=True)
            db().execute("UPDATE parcels SET name='Anonymised',phone='',address='Anonymised',proof=NULL WHERE id=?",(row['id'],))
        audit('retention_anonymization')
    print(f'Anonymised {len(rows)} delivered parcels.')
