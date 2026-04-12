import bcrypt
from db import get_conn
from routes.auth import require_auth, require_role

def list_users(req):
    require_role(req, 'abc_staff')
    conn = get_conn()

    users = conn.execute("""
        SELECT id, name, email, role, is_active, last_login, created_at
        FROM users
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return 200, [dict(u) for u in users]

def create_user(req):
    require_role(req, 'abc_staff')
    b = req['body']

    name = b.get('name', '').strip()
    email = (b.get('email') or '').lower().strip()
    password = b.get('password', '').strip()
    role = b.get('role', '').strip()

    if not name:
        raise ValueError('name is required')

    if not email:
        raise ValueError('email is required')

    if not password:
        raise ValueError('password is required')

    if role not in ('sreedhanya_staff', 'abc_staff'):
        raise ValueError('role must be "sreedhanya_staff" or "abc_staff"')

    conn = get_conn()

    # Check if email already exists
    existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        conn.close()
        raise ValueError('Email already exists')

    # Hash password
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    c = conn.cursor()
    c.execute("""
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """, (name, email, password_hash, role))

    conn.commit()
    user_id = c.lastrowid
    conn.close()

    return 201, {'success': True, 'id': user_id}

def update_user(req):
    require_role(req, 'abc_staff')
    user_id = req['params']['id']
    b = req['body']

    name = b.get('name', '').strip()
    role = b.get('role', '').strip()
    is_active = b.get('is_active')
    password = b.get('password', '').strip()

    if not name:
        raise ValueError('name is required')

    if role and role not in ('sreedhanya_staff', 'abc_staff'):
        raise ValueError('role must be "sreedhanya_staff" or "abc_staff"')

    conn = get_conn()

    # Verify user exists
    user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        raise ValueError('User not found')

    c = conn.cursor()

    # Build update query
    if password:
        # Hash new password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("""
            UPDATE users SET name = ?, role = ?, is_active = ?, password_hash = ?
            WHERE id = ?
        """, (name, role if role else None, 1 if is_active else 0, password_hash, user_id))
    else:
        c.execute("""
            UPDATE users SET name = ?, role = ?, is_active = ?
            WHERE id = ?
        """, (name, role if role else None, 1 if is_active else 0, user_id))

    conn.commit()
    conn.close()

    return 200, {'success': True}

user_routes = {
    ('GET',  '/api/users'):      list_users,
    ('POST', '/api/users'):      create_user,
    ('PUT',  '/api/users/<id>'): update_user,
}
