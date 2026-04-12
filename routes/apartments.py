from db import get_conn
from routes.auth import require_auth

def list_apartments(req):
    require_auth(req)
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*,
          (SELECT COUNT(*) FROM requests r WHERE r.apartment_id = a.id) AS request_count,
          (SELECT COUNT(*) FROM requests r WHERE r.apartment_id = a.id AND r.status='pending_review') AS pending_review_count,
          (SELECT COUNT(*) FROM quotations q WHERE q.apartment_id = a.id AND q.status='confirmed') AS confirmed_quotes,
          (SELECT COUNT(*) FROM payment_milestones pm
            JOIN quotations q ON pm.quote_id = q.id
            WHERE q.apartment_id = a.id AND pm.status='overdue') AS overdue_payments
        FROM apartments a ORDER BY a.block, a.floor, a.apartment_number
    """).fetchall()
    conn.close()
    return 200, [dict(r) for r in rows]

def get_apartment(req):
    require_auth(req)
    apt_id = req['params']['id']
    conn = get_conn()
    apt = conn.execute('SELECT * FROM apartments WHERE id = ?', (apt_id,)).fetchone()
    if not apt:
        conn.close()
        raise ValueError('Apartment not found')

    requests = conn.execute("""
        SELECT r.*, c.item_name AS catalogue_item_name, u.name AS created_by_name,
          vr.decision AS review_decision, vr.reason AS review_reason, vr.reviewed_at,
          rv.name AS reviewed_by_name
        FROM requests r
        LEFT JOIN catalogue c ON r.catalogue_item_id = c.id
        LEFT JOIN users u ON r.created_by = u.id
        LEFT JOIN viability_reviews vr ON vr.request_id = r.id
        LEFT JOIN users rv ON vr.reviewed_by = rv.id
        WHERE r.apartment_id = ? ORDER BY r.created_at DESC
    """, (apt_id,)).fetchall()

    quotations = conn.execute("""
        SELECT q.*, u.name AS generated_by_name FROM quotations q
        JOIN users u ON q.generated_by = u.id
        WHERE q.apartment_id = ? ORDER BY q.version DESC
    """, (apt_id,)).fetchall()

    payments = conn.execute("""
        SELECT pm.*, q.version AS quote_version, q.total_amount AS quote_net_total
        FROM payment_milestones pm
        JOIN quotations q ON pm.quote_id = q.id
        WHERE q.apartment_id = ? ORDER BY q.version ASC, pm.id
    """, (apt_id,)).fetchall()

    stages = conn.execute("""
        SELECT ps.*, q.version AS quote_version FROM project_stages ps
        JOIN quotations q ON ps.quote_id = q.id
        WHERE q.apartment_id = ? ORDER BY q.version ASC, ps.stage_number
    """, (apt_id,)).fetchall()

    invoices = conn.execute("""
        SELECT i.* FROM invoices i
        JOIN quotations q ON i.quote_id = q.id
        WHERE q.apartment_id = ? ORDER BY i.generated_at DESC
    """, (apt_id,)).fetchall()

    conn.close()
    return 200, {
        **dict(apt),
        'requests':   [dict(r) for r in requests],
        'quotations': [dict(q) for q in quotations],
        'payments':   [dict(p) for p in payments],
        'stages':     [dict(s) for s in stages],
        'invoices':   [dict(i) for i in invoices],
    }

def update_apartment(req):
    require_auth(req)
    b = req['body']
    conn = get_conn()
    conn.execute(
        'UPDATE apartments SET owner_name=?, owner_phone=?, owner_email=? WHERE id=?',
        (b.get('owner_name'), b.get('owner_phone'), b.get('owner_email'), req['params']['id'])
    )
    conn.commit()
    conn.close()
    return 200, {'success': True}

apartment_routes = {
    ('GET',  '/api/apartments'):      list_apartments,
    ('GET',  '/api/apartments/<id>'): get_apartment,
    ('PUT',  '/api/apartments/<id>'): update_apartment,
}
