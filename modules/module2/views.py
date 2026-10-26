"""YOUR MODULE: separate registration, list, detail and public tracking pages."""
from flask import render_template, g, redirect, url_for
from shared import db, accessible
from .routes import bp, parcels

def require_seller():
    if not g.user: return redirect(url_for('module1.login_page'))
    if g.user['role']!='seller': return render_template('error.html',title='Access restricted',message='This workspace is for sellers.'),403

@bp.get('/parcels')
def parcels_page():
    denied=require_seller()
    if denied is not None: return denied
    result=parcels()
    if isinstance(result,tuple): return result
    return render_template('module2/my_parcels.html',title='My parcels',parcels=result.get_json()['parcels'])

@bp.get('/parcels/new')
def register_parcel_page():
    denied=require_seller()
    if denied is not None: return denied
    return render_template('module2/register_parcel.html',title='Register parcel')

@bp.get('/parcels/<int:parcel_id>')
def parcel_details_page(parcel_id):
    denied=require_seller()
    if denied is not None: return denied
    # M2 SECURITY: authorize the HTML page as well as the API endpoint.
    parcel=accessible(parcel_id)
    if not parcel: return render_template('error.html',title='Parcel not found',message='Parcel not found.'),404
    history=db().execute('SELECT status,created FROM history WHERE parcel_id=? ORDER BY id',(parcel_id,)).fetchall()
    return render_template('module2/parcel_details.html',title='Parcel details',parcel=parcel,history=history)

@bp.get('/track')
def public_tracking_page():
    return render_template('module2/public_tracking.html',title='Public tracking')
