"""Member 3: delivery and dashboard HTML pages."""
from flask import render_template, g, redirect, url_for
from shared import db, accessible
from .routes import bp

def require_role(*roles):
    if not g.user: return redirect(url_for('module1.login_page'))
    if g.user['role'] not in roles: return render_template('error.html',title='Access restricted',message='You do not have access to this workspace.'),403

@bp.get('/deliveries')
def deliveries_page():
    denied=require_role('admin','rider')
    if denied is not None:return denied
    if g.user['role']=='admin': parcels=db().execute('SELECT * FROM parcels ORDER BY id DESC LIMIT 200').fetchall()
    else: parcels=db().execute('SELECT * FROM parcels WHERE rider_id=? ORDER BY id DESC LIMIT 200',(g.user['id'],)).fetchall()
    return render_template('module3/deliveries.html',title='Deliveries',parcels=parcels)

@bp.get('/deliveries/<int:parcel_id>')
def delivery_details_page(parcel_id):
    denied=require_role('admin','rider')
    if denied is not None:return denied
    parcel=accessible(parcel_id)
    if not parcel:return render_template('error.html',title='Parcel not found',message='Parcel not found.'),404
    riders=db().execute("SELECT id,name FROM users WHERE role='rider' AND active=1").fetchall() if g.user['role']=='admin' else []
    history=db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(parcel_id,)).fetchall()
    return render_template('module3/delivery_details.html',title='Delivery details',parcel=parcel,riders=riders,history=history)

@bp.get('/dashboard')
def dashboard_page():
    denied=require_role('admin')
    if denied is not None:return denied
    counts={r['status']:r['n'] for r in db().execute('SELECT status,count(*) n FROM parcels GROUP BY status')}
    events=db().execute('SELECT actor_id,event,created FROM audit ORDER BY id DESC LIMIT 30').fetchall()
    return render_template('module3/dashboard.html',title='Admin dashboard',counts=counts,statuses=['Registered','Assigned','Out for Delivery','Delivered','Failed'],events=events)
