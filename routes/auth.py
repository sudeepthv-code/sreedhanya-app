from datetime import datetime, timezone, timedelta
import bcrypt, jwt as pyjwt
from db import get_conn

def require_auth(req):
    if not req['user']:
        raise PermissionError('Authentication required')

def require_role(req, *roles):
    require_auth(req)
    if req['user']['role'] not in roles:
        raise PermissionError('Access denied')

def login(req):
    body = req['body']
    email = (body.get('email') or '').lower().strip()
    password = body.get('password') or ''
    if not email or not password:
        raise ValueError('Email and password required')

    conn = get_conn()
    user = conn.execute(
        'SELECT * FROM users WHERE email = ? AND is_active = 1', (email,)
    ).fetchone()

    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        conn.close()
        raise PermissionError('Invalid credentials')

    conn.execute('UPDATE users SET last_login = datetime("now") WHERE id = ?', (user['id'],))
    conn.commit()
    conn.close()

    token = pyjwt.encode(
        {'id': user['id'], 'role': user['role'],
         'exp': datetime.now(timezone.utc) + timedelta(hours=8)},
        req['jwt_secret'], algorithm='HS256'
    )
    return 200, {
        'token': token,
        'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']}
    }

def me(req):
    require_auth(req)
    return 200, {'user': req['user']}

auth_routes = {
    ('POST', '/api/auth/login'): login,
    ('GET',  '/api/auth/me'):    me,
}
