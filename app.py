"""ParcelTrack assignment. M1 authentication; M2 parcels/tracking; M3 delivery/admin."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.vendor'))
import io
import os
import re
import math
import secrets
import sqlite3
import time
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, g, render_template, send_file
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from PIL import Image, UnidentifiedImageError

hasher = PasswordHasher()
STATUSES = ['Registered', 'Assigned', 'Out for Delivery', 'Delivered', 'Failed']

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=str(ROOT/'instance'/'parceltrack.db'), UPLOADS=str(ROOT/'instance'/'proofs'), MAX_CONTENT_LENGTH=3*1024*1024, HTTPS=os.getenv('PARCELTRACK_HTTPS') == '1')
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOADS']).mkdir(parents=True, exist_ok=True)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        if 'db' in g:
            g.db.close()

    with app.app_context():
        db().executescript((ROOT/'database'/'schema.sql').read_text())

    def fail(message, status=400):
        return jsonify(error=message), status

    def audit(event, actor=None):
        # SHARED SECURITY P5: fixed event names only; no passwords/addresses in logs.
        db().execute('INSERT INTO audit(actor_id,event) VALUES (?,?)', (actor, event))

    def limited(bucket, maximum, seconds):
        # M2 SECURITY: persistent, atomic per-IP limiter; never trust X-Forwarded-For.
        key = bucket + ':' + (request.remote_addr or 'local')
        now = time.time()
        with db():
            db().execute('INSERT INTO limits VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=CASE WHEN reset<? THEN 1 ELSE count+1 END, reset=CASE WHEN reset<? THEN excluded.reset ELSE reset END', (key, now+seconds, now, now))
            row = db().execute('SELECT count FROM limits WHERE bucket=?', (key,)).fetchone()
        return row['count'] > maximum

    @app.before_request
    def authenticate():
        g.user = None
        token = request.cookies.get('pt_session', '')
        row = db().execute('SELECT s.csrf,s.expires,u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND u.active=1', (token,)).fetchone()
        if row and row['expires'] > time.time():
            g.user = row
        # SHARED SECURITY: all authenticated mutations require a session-bound CSRF token.
        if request.method in ('POST','PATCH','DELETE') and request.path not in ('/api/login','/api/register'):
            if not g.user:
                return fail('Please sign in to continue.', 401)
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''), g.user['csrf']):
                return fail('Your form expired. Refresh and try again.', 403)
        if request.method in ('POST','PATCH','DELETE'):
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                return fail('Request origin is not allowed.', 403)

    @app.after_request
    def headers(response):
        response.headers.update({'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'", 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'Cache-Control':'no-store', 'Permissions-Policy':'camera=(), microphone=(), geolocation=()'})
        if app.config['HTTPS']:
            response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    def role(*roles):
        def decorate(fn):
            @wraps(fn)
            def check(*args, **kwargs):
                if not g.user:
                    return fail('Please sign in to continue.',401)
                if g.user['role'] not in roles:
                    return fail('You do not have access to this action.',403)
                return fn(*args, **kwargs)
            return check
        return decorate

    def payload():
        value = request.get_json(silent=True)
        return value if isinstance(value,dict) else {}

    def text(value, maximum, minimum=1):
        return isinstance(value,str) and minimum <= len(value.strip()) <= maximum and not any(ord(c)<32 and c not in '\n\r' for c in value)

    def credentials(data):
        return text(data.get('name'),80,2) and text(data.get('email'),150) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']) and isinstance(data.get('password'),str) and 10 <= len(data['password']) <= 128

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.get('/api/me')
    def me():
        return jsonify(user={k:g.user[k] for k in ('id','name','email','role')} if g.user else None, csrf=g.user['csrf'] if g.user else None)

    @app.post('/api/register')
    def register():
        if limited('register',10,3600): return fail('Too many attempts. Try again later.',429)
        data=payload()
        if not credentials(data): return fail('Use a valid name, email and a password of 10–128 characters.')
        try:
            with db():
                db().execute('INSERT INTO users(name,email,password,role) VALUES (?,?,?,?)',(data['name'].strip(),data['email'].strip().lower(),hasher.hash(data['password']),'seller'))
                audit('seller_registered')
        except sqlite3.IntegrityError:
            return fail('Unable to register with these details.',409)
        return jsonify(message='Account created. You can now sign in.'),201

    @app.post('/api/login')
    def login():
        if limited('login',10,300): return fail('Too many sign-in attempts. Try again in five minutes.',429)
        data=payload()
        if not text(data.get('email'),150) or not isinstance(data.get('password'),str) or len(data['password'])>128:
            return fail('Email or password is incorrect.',401)
        user=db().execute('SELECT * FROM users WHERE email=? AND active=1',(data['email'].strip().lower(),)).fetchone()
        try:
            hasher.verify(user['password'] if user else dummy_hash,data['password'])
            if not user: raise ValueError()
        except (VerificationError,InvalidHashError,ValueError):
            with db(): audit('login_failed')
            return fail('Email or password is incorrect.',401)
        token=secrets.token_urlsafe(32)
        with db():
            db().execute('DELETE FROM sessions WHERE token=? OR expires<?',(request.cookies.get('pt_session',''),time.time()))
            db().execute('INSERT INTO sessions VALUES (?,?,?,?)',(token,user['id'],secrets.token_urlsafe(32),time.time()+3600))
            audit('login_success',user['id'])
        response=jsonify(message='Welcome back.')
        response.set_cookie('pt_session',token,httponly=True,secure=app.config['HTTPS'],samesite='Lax',max_age=3600)
        return response

    dummy_hash=hasher.hash(secrets.token_urlsafe(32))

    @app.post('/api/logout')
    def logout():
        with db(): db().execute('DELETE FROM sessions WHERE token=?',(request.cookies.get('pt_session',''),))
        response=jsonify(message='Signed out.')
        response.delete_cookie('pt_session')
        return response

    @app.post('/api/password')
    @role('seller','rider','admin')
    def password():
        data=payload()
        if limited('password',10,300): return fail('Too many attempts.',429)
        if not isinstance(data.get('password'),str) or not 10<=len(data['password'])<=128: return fail('New password must contain 10–128 characters.')
        try: hasher.verify(g.user['password'],str(data.get('current',''))[:129])
        except (VerificationError,InvalidHashError): return fail('Current password is incorrect.',403)
        with db():
            db().execute('UPDATE users SET password=? WHERE id=?',(hasher.hash(data['password']),g.user['id']))
            db().execute('DELETE FROM sessions WHERE user_id=?',(g.user['id'],))
            audit('password_changed',g.user['id'])
        return jsonify(message='Password changed. Please sign in again.')

    def accessible(parcel_id):
        # M2 SECURITY P1: enforce ownership for EVERY parcel ID, including proof access.
        sql='SELECT * FROM parcels WHERE id=?'
        args=[parcel_id]
        if g.user['role']=='seller': sql+=' AND seller_id=?'; args.append(g.user['id'])
        if g.user['role']=='rider': sql+=' AND rider_id=?'; args.append(g.user['id'])
        return db().execute(sql,args).fetchone()

    @app.get('/api/parcels')
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

    @app.post('/api/parcels')
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

    @app.get('/api/parcels/<int:parcel_id>')
    @role('seller','rider','admin')
    def detail(parcel_id):
        row=accessible(parcel_id)
        if not row: return fail('Parcel not found.',404)
        return jsonify(parcel=dict(row),history=[dict(r) for r in db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(parcel_id,))])

    @app.get('/api/track')
    def track():
        # M2 SECURITY P3: allowlist public fields; no recipient or actor information.
        if limited('tracking',30,60): return fail('Too many lookups. Please wait one minute.',429)
        tracking=request.args.get('number','').upper()
        if not re.fullmatch(r'KC-[A-F0-9]{32}',tracking): return fail('No parcel found. Check your tracking number.',404)
        row=db().execute('SELECT id FROM parcels WHERE tracking=?',(tracking,)).fetchone()
        if not row: return fail('No parcel found. Check your tracking number.',404)
        return jsonify(history=[dict(r) for r in db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(row['id'],))])

    @app.get('/api/admin')
    @role('admin')
    def admin():
        return jsonify(users=[dict(r) for r in db().execute('SELECT id,name,email,role,active FROM users ORDER BY id')],counts={r['status']:r['n'] for r in db().execute('SELECT status,count(*) n FROM parcels GROUP BY status')},audit=[dict(r) for r in db().execute('SELECT actor_id,event,created FROM audit ORDER BY id DESC LIMIT 30')])

    @app.post('/api/users')
    @role('admin')
    def add_rider():
        data=payload()
        if not credentials(data): return fail('Enter a valid name, email and password of 10–128 characters.')
        try:
            with db():
                db().execute('INSERT INTO users(name,email,password,role) VALUES (?,?,?,?)',(data['name'].strip(),data['email'].strip().lower(),hasher.hash(data['password']),'rider'))
                audit('rider_created',g.user['id'])
        except sqlite3.IntegrityError: return fail('Unable to create account with these details.',409)
        return jsonify(message='Rider account created.'),201

    @app.post('/api/users/<int:user_id>/toggle')
    @role('admin')
    def toggle(user_id):
        user=db().execute('SELECT * FROM users WHERE id=? AND role!=?',(user_id,'admin')).fetchone()
        if not user: return fail('Account not found.',404)
        with db():
            db().execute('UPDATE users SET active=1-active WHERE id=?',(user_id,))
            db().execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
            audit('account_access_changed',g.user['id'])
        return jsonify(message='Account access updated.')

    @app.post('/api/parcels/<int:parcel_id>/assign')
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

    @app.post('/api/parcels/<int:parcel_id>/status')
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
                    image.convert('RGB').save(Path(app.config['UPLOADS'])/filename,'JPEG',quality=85)
            except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError): return fail('The file is not a valid JPG or PNG photo.')
        try:
            with db():
                cur=db().execute('UPDATE parcels SET status=?,proof=COALESCE(?,proof) WHERE id=? AND rider_id=? AND status=?',(status,filename,parcel_id,g.user['id'],row['status']))
                if not cur.rowcount:
                    if filename: (Path(app.config['UPLOADS'])/filename).unlink(missing_ok=True)
                    return fail('Parcel changed. Refresh and try again.',409)
                db().execute('INSERT INTO history(parcel_id,status,actor_id) VALUES (?,?,?)',(parcel_id,status,g.user['id']))
                audit('delivery_status_changed',g.user['id'])
        except sqlite3.Error:
            if filename: (Path(app.config['UPLOADS'])/filename).unlink(missing_ok=True)
            raise
        return jsonify(message='Delivery updated.')

    @app.get('/api/parcels/<int:parcel_id>/proof')
    @role('seller','rider','admin')
    def proof(parcel_id):
        row=accessible(parcel_id)
        if not row or not row['proof']: return fail('Photo not found.',404)
        return send_file(Path(app.config['UPLOADS'])/row['proof'],mimetype='image/jpeg')

    @app.cli.command('create-admin')
    def create_admin():
        """Provision admin interactively; passwords never appear in source or arguments."""
        import getpass
        name=input('Admin name: ').strip(); email=input('Admin email: ').strip().lower()
        password=getpass.getpass('Password (10+ characters): ')
        if not credentials(dict(name=name,email=email,password=password)): print('Invalid details.'); return
        with db(): db().execute('INSERT INTO users(name,email,password,role) VALUES (?,?,?,?)',(name,email,hasher.hash(password),'admin'))
        print('Admin created.')

    @app.cli.command('anonymize')
    def anonymize():
        # P3 retention: run daily via OS scheduler; keep status-only history.
        cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
        rows=db().execute("SELECT p.id,p.proof FROM parcels p WHERE p.status='Delivered' AND EXISTS(SELECT 1 FROM history h WHERE h.parcel_id=p.id AND h.status='Delivered' AND h.created<?)",(cutoff,)).fetchall()
        with db():
            for row in rows:
                if row['proof']: (Path(app.config['UPLOADS'])/row['proof']).unlink(missing_ok=True)
                db().execute("UPDATE parcels SET name='Anonymised',phone='',address='Anonymised',proof=NULL WHERE id=?",(row['id'],))
            audit('retention_anonymization')
        print(f'Anonymised {len(rows)} delivered parcels.')

    @app.errorhandler(413)
    def too_large(error): return fail('Request too large. Photos must be at most 2 MB.',413)

    @app.errorhandler(404)
    def missing(error): return fail('Page or record not found.',404)

    @app.errorhandler(Exception)
    def unexpected(error):
        # SHARED SECURITY: no SQL, stack trace or personal data sent to the browser/log.
        app.logger.error('Request failed: %s',type(error).__name__)
        return fail('Unable to complete this request. Please try again.',500)

    return app

if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=5000,debug=False)
