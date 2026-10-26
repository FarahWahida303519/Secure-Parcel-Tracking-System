"""Login and User Management — Member 1."""
import secrets
import sqlite3
import time
from flask import Blueprint, current_app, request, jsonify, g
from argon2.exceptions import VerificationError, InvalidHashError
from shared import db, fail, audit, limited, role, payload, text, credentials, hasher

bp = Blueprint('module1', __name__, cli_group=None)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))

@bp.get('/api/me')
def me():
    return jsonify(user={k:g.user[k] for k in ('id','name','email','role')} if g.user else None, csrf=g.user['csrf'] if g.user else None)

@bp.post('/api/register')
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

@bp.post('/api/login')
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
    response.set_cookie('pt_session',token,httponly=True,secure=current_app.config['HTTPS'],samesite='Lax',max_age=3600)
    return response

@bp.post('/api/logout')
def logout():
    with db(): db().execute('DELETE FROM sessions WHERE token=?',(request.cookies.get('pt_session',''),))
    response=jsonify(message='Signed out.')
    response.delete_cookie('pt_session')
    return response

@bp.post('/api/password')
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

@bp.post('/api/users')
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

@bp.post('/api/users/<int:user_id>/toggle')
@role('admin')
def toggle(user_id):
    user=db().execute('SELECT * FROM users WHERE id=? AND role!=?',(user_id,'admin')).fetchone()
    if not user: return fail('Account not found.',404)
    with db():
        db().execute('UPDATE users SET active=1-active WHERE id=?',(user_id,))
        db().execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
        audit('account_access_changed',g.user['id'])
    return jsonify(message='Account access updated.')

@bp.cli.command('create-admin')
def create_admin():
    """Provision admin interactively; passwords never appear in source or arguments."""
    import getpass
    name=input('Admin name: ').strip(); email=input('Admin email: ').strip().lower()
    password=getpass.getpass('Password (10+ characters): ')
    if not credentials(dict(name=name,email=email,password=password)): print('Invalid details.'); return
    with db(): db().execute('INSERT INTO users(name,email,password,role) VALUES (?,?,?,?)',(name,email,hasher.hash(password),'admin'))
    print('Admin created.')
