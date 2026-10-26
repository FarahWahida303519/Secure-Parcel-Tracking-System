"""Shared database, session, authorization and security helpers. Group-owned."""
import io
import re
import math
import secrets
import sqlite3
import time
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import Blueprint, current_app, request, jsonify, g, render_template, send_file, redirect, url_for
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException

hasher = PasswordHasher()

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

def close_db(error):
    if 'db' in g:
        g.db.close()

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

def headers(response):
    response.headers.update({'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'", 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'Cache-Control':'no-store', 'Permissions-Policy':'camera=(), microphone=(), geolocation=()'})
    if current_app.config['HTTPS']:
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

def accessible(parcel_id):
    # M2 SECURITY P1: enforce ownership for EVERY parcel ID, including proof access.
    sql='SELECT * FROM parcels WHERE id=?'
    args=[parcel_id]
    if g.user['role']=='seller': sql+=' AND seller_id=?'; args.append(g.user['id'])
    if g.user['role']=='rider': sql+=' AND rider_id=?'; args.append(g.user['id'])
    return db().execute(sql,args).fetchone()

def too_large(error): return fail('Request too large. Photos must be at most 2 MB.',413)

def missing(error): return fail('Page or record not found.',404)

def unexpected(error):
    if isinstance(error, HTTPException):
        return fail('Request could not be processed.', error.code)
    # SHARED SECURITY: no SQL, stack trace or personal data sent to the browser/log.
    current_app.logger.error('Request failed: %s',type(error).__name__)
    return fail('Unable to complete this request. Please try again.',500)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.before_request(authenticate)
    app.after_request(headers)
    app.register_error_handler(413, too_large)
    app.register_error_handler(404, missing)
    app.register_error_handler(Exception, unexpected)
