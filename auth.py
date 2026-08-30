from functools import wraps
from flask import session, redirect, url_for, flash
from database import get_db


def current_user():
    uid = session.get('user_id')
    if uid is None:
        return None
    return get_db().execute(
        'SELECT * FROM users WHERE id = ?', (uid,)
    ).fetchone()


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                flash('Please log in first.')
                return redirect(url_for('login'))
            if role and user['role'] != role:
                flash(f'This page is for {role}s only.')
                return redirect(url_for('home'))
            return view(*args, **kwargs)
        return wrapped
    return decorator