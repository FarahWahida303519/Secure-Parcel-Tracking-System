"""Member 1: HTML pages for login, registration, accounts and user management."""
from flask import render_template, g, redirect, url_for
from shared import db
from .routes import bp

@bp.get('/login')
def login_page():
    return render_template('module1/login.html', title='Sign in')

@bp.get('/register')
def register_page():
    return render_template('module1/register.html', title='Create account')

@bp.get('/account')
def account_page():
    if not g.user: return redirect(url_for('module1.login_page'))
    return render_template('module1/account.html', title='Account')

@bp.get('/users')
def users_page():
    if not g.user: return redirect(url_for('module1.login_page'))
    if g.user['role']!='admin': return render_template('error.html',title='Access restricted',message='Only administrators can manage accounts.'),403
    users=db().execute('SELECT id,name,email,role,active FROM users ORDER BY id').fetchall()
    return render_template('module1/users.html', title='User management', users=users)
