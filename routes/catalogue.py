from datetime import datetime
from db import get_conn
from routes.auth import require_auth, require_role

def list_catalogue(req):
    require_auth(req)
    conn = get_conn()

    # Check if 'all' query param exists to include inactive items
    include_all = 'all' in req['query']

    if include_all:
        rows = conn.execute("""
            SELECT c.*, u.name AS added_by_name
            FROM catalogue c
            LEFT JOIN users u ON c.added_by = u.id
            ORDER BY c.item_name
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT c.*, u.name AS added_by_name
            FROM catalogue c
            LEFT JOIN users u ON c.added_by = u.id
            WHERE c.is_active = 1
            ORDER BY c.item_name
        """).fetchall()

    conn.close()
    return 200, [dict(r) for r in rows]

def get_catalogue_item(req):
    require_auth(req)
    item_id = req['params']['id']
    conn = get_conn()

    item = conn.execute("""
        SELECT c.*, u.name AS added_by_name
        FROM catalogue c
        LEFT JOIN users u ON c.added_by = u.id
        WHERE c.id = ?
    """, (item_id,)).fetchone()

    conn.close()

    if not item:
        raise ValueError('Catalogue item not found')

    return 200, dict(item)

def create_catalogue_item(req):
    require_role(req, 'abc_staff')
    b = req['body']

    # Validate required fields
    item_name = b.get('item_name', '').strip()
    if not item_name:
        raise ValueError('item_name is required')

    description = b.get('description', '').strip()
    key_materials = b.get('key_materials', '').strip()
    default_unit = b.get('default_unit', 'per unit').strip()
    default_unit_price = b.get('default_unit_price', 0)
    labour_included = 1 if b.get('labour_included') else 0
    notes = b.get('notes', '').strip()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        INSERT INTO catalogue
            (item_name, description, key_materials, default_unit, default_unit_price,
             labour_included, is_custom, added_by, notes)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (item_name, description, key_materials, default_unit, default_unit_price,
          labour_included, req['user']['id'], notes))

    conn.commit()
    item_id = c.lastrowid
    conn.close()

    return 201, {'success': True, 'id': item_id}

def update_catalogue_item(req):
    require_role(req, 'abc_staff')
    item_id = req['params']['id']
    b = req['body']

    # Check if item exists
    conn = get_conn()
    item = conn.execute('SELECT id FROM catalogue WHERE id = ?', (item_id,)).fetchone()
    if not item:
        conn.close()
        raise ValueError('Catalogue item not found')

    # Update fields
    item_name = b.get('item_name', '').strip()
    if not item_name:
        conn.close()
        raise ValueError('item_name is required')

    description = b.get('description', '').strip()
    key_materials = b.get('key_materials', '').strip()
    default_unit = b.get('default_unit', 'per unit').strip()
    default_unit_price = b.get('default_unit_price', 0)
    labour_included = 1 if b.get('labour_included') else 0
    notes = b.get('notes', '').strip()
    is_active = 1 if b.get('is_active', True) else 0

    c = conn.cursor()
    c.execute("""
        UPDATE catalogue
        SET item_name = ?, description = ?, key_materials = ?, default_unit = ?,
            default_unit_price = ?, labour_included = ?, notes = ?, is_active = ?,
            updated_at = datetime('now')
        WHERE id = ?
    """, (item_name, description, key_materials, default_unit, default_unit_price,
          labour_included, notes, is_active, item_id))

    conn.commit()
    conn.close()

    return 200, {'success': True}

def toggle_catalogue_item(req):
    require_role(req, 'abc_staff')
    item_id = req['params']['id']

    conn = get_conn()
    item = conn.execute('SELECT is_active FROM catalogue WHERE id = ?', (item_id,)).fetchone()

    if not item:
        conn.close()
        raise ValueError('Catalogue item not found')

    new_status = 1 - item['is_active']

    c = conn.cursor()
    c.execute("""
        UPDATE catalogue
        SET is_active = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (new_status, item_id))

    conn.commit()
    conn.close()

    return 200, {'success': True, 'is_active': new_status}

catalogue_routes = {
    ('GET',  '/api/catalogue'):      list_catalogue,
    ('GET',  '/api/catalogue/<id>'): get_catalogue_item,
    ('POST', '/api/catalogue'):      create_catalogue_item,
    ('PUT',  '/api/catalogue/<id>'): update_catalogue_item,
    ('PATCH', '/api/catalogue/<id>/toggle'): toggle_catalogue_item,
}
