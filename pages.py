"""Shared landing page. Module pages live with their owners."""
from flask import Blueprint, render_template
bp = Blueprint('pages', __name__)
@bp.get('/')
def home():
    return render_template('index.html', title='Overview')
