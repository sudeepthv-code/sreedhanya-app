from datetime import datetime
from db import get_conn
from routes.auth import require_auth, require_role

def list_requests(req):
    require_auth(req)
    conn = get_conn()

    # Build query with optional filters
    query = """
        SELECT r.*,
               a.apartment_number, a.bedroom_type, a.owner_name, a.owner_email,
               c.item_name AS catalogue_item_name,
               u.name AS created_by_name,
               vr.id AS review_id, vr.decision AS review_decision, vr.reason AS review_reason,
               rv.name AS reviewed_by_name
        FROM requests r
        JOIN apartments a ON r.apartment_id = a.id
        LEFT JOIN catalogue c ON r.catalogue_item_id = c.id
        LEFT JOIN users u ON r.created_by = u.id
        LEFT JOIN viability_reviews vr ON vr.request_id = r.id
        LEFT JOIN users rv ON vr.reviewed_by = rv.id
        WHERE 1=1
    """

    params = []

    # Filter by status if provided
    status = req['query'].get('status')
    if status:
        query += " AND r.status = ?"
        params.append(status)

    # Filter by apartment_id if provided
    apartment_id = req['query'].get('apartment_id')
    if apartment_id:
        query += " AND r.apartment_id = ?"
        params.append(apartment_id)

    query += " ORDER BY r.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return 200, [dict(r) for r in rows]

def get_request(req):
    require_auth(req)
    request_id = req['params']['id']
    conn = get_conn()

    request_obj = conn.execute("""
        SELECT r.*,
               a.apartment_number, a.bedroom_type, a.owner_name, a.owner_email,
               c.item_name AS catalogue_item_name,
               u.name AS created_by_name,
               vr.id AS review_id, vr.decision AS review_decision, vr.reason AS review_reason,
               rv.name AS reviewed_by_name
        FROM requests r
        JOIN apartments a ON r.apartment_id = a.id
        LEFT JOIN catalogue c ON r.catalogue_item_id = c.id
        LEFT JOIN users u ON r.created_by = u.id
        LEFT JOIN viability_reviews vr ON vr.request_id = r.id
        LEFT JOIN users rv ON vr.reviewed_by = rv.id
        WHERE r.id = ?
    """, (request_id,)).fetchone()

    conn.close()

    if not request_obj:
        raise ValueError('Request not found')

    return 200, dict(request_obj)

def create_requests(req):
    require_role(req, 'sreedhanya_staff')
    b = req['body']

    apartment_id = b.get('apartment_id')
    items = b.get('items', [])

    if not apartment_id:
        raise ValueError('apartment_id is required')

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError('items array is required and must not be empty')

    conn = get_conn()

    # Verify apartment exists
    apt = conn.execute('SELECT id, status FROM apartments WHERE id = ?', (apartment_id,)).fetchone()
    if not apt:
        conn.close()
        raise ValueError('Apartment not found')

    c = conn.cursor()
    created_ids = []

    # Insert each item
    for item in items:
        room = item.get('room', '').strip()
        catalogue_item_id = item.get('catalogue_item_id')
        custom_item_name = item.get('custom_item_name', '').strip()
        description = item.get('description', '').strip()

        if not room:
            conn.close()
            raise ValueError('room is required for each item')

        c.execute("""
            INSERT INTO requests
                (apartment_id, created_by, room, catalogue_item_id, custom_item_name, description, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending_review')
        """, (apartment_id, req['user']['id'], room, catalogue_item_id, custom_item_name, description))

        created_ids.append(c.lastrowid)

    # Update apartment status if currently 'no_request'
    if apt['status'] == 'no_request':
        c.execute(
            "UPDATE apartments SET status = 'in_progress' WHERE id = ?",
            (apartment_id,)
        )

    conn.commit()
    conn.close()

    return 201, {'success': True, 'ids': created_ids}

def review_request(req):
    require_role(req, 'abc_staff')
    request_id = req['params']['id']
    b = req['body']

    decision = b.get('decision', '').strip()
    reason = b.get('reason', '').strip()

    if decision not in ('viable', 'not_viable'):
        raise ValueError('decision must be "viable" or "not_viable"')

    if decision == 'not_viable' and not reason:
        raise ValueError('reason is required when decision is "not_viable"')

    conn = get_conn()

    # Verify request exists
    req_obj = conn.execute('SELECT id FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not req_obj:
        conn.close()
        raise ValueError('Request not found')

    c = conn.cursor()

    # Delete any existing review for this request
    c.execute('DELETE FROM viability_reviews WHERE request_id = ?', (request_id,))

    # Insert new review
    c.execute("""
        INSERT INTO viability_reviews (request_id, reviewed_by, decision, reason)
        VALUES (?, ?, ?, ?)
    """, (request_id, req['user']['id'], decision, reason if reason else None))

    # Update request status
    c.execute(
        "UPDATE requests SET status = ? WHERE id = ?",
        (decision, request_id)
    )

    conn.commit()
    conn.close()

    return 200, {'success': True}

request_routes = {
    ('GET',  '/api/requests'):           list_requests,
    ('GET',  '/api/requests/<id>'):      get_request,
    ('POST', '/api/requests'):           create_requests,
    ('POST', '/api/requests/<id>/review'): review_request,
}
