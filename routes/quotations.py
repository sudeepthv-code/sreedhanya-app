from datetime import datetime
from db import get_conn
from routes.auth import require_auth, require_role
from services.pdf import generate_quote_pdf

def list_quotations(req):
    require_auth(req)
    conn = get_conn()

    query = """
        SELECT q.*, u.name AS generated_by_name, a.apartment_number, a.bedroom_type, a.owner_name
        FROM quotations q
        JOIN users u ON q.generated_by = u.id
        JOIN apartments a ON q.apartment_id = a.id
        WHERE 1=1
    """

    params = []

    # Filter by apartment_id if provided
    apartment_id = req['query'].get('apartment_id')
    if apartment_id:
        query += " AND q.apartment_id = ?"
        params.append(apartment_id)

    query += " ORDER BY q.generated_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return 200, [dict(r) for r in rows]

def get_quotation(req):
    require_auth(req)
    quote_id = req['params']['id']
    conn = get_conn()

    quote = conn.execute("""
        SELECT q.*, u.name AS generated_by_name, a.apartment_number, a.bedroom_type, a.owner_name
        FROM quotations q
        JOIN users u ON q.generated_by = u.id
        JOIN apartments a ON q.apartment_id = a.id
        WHERE q.id = ?
    """, (quote_id,)).fetchone()

    if not quote:
        conn.close()
        raise ValueError('Quotation not found')

    # Get quote items
    items = conn.execute("""
        SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id
    """, (quote_id,)).fetchall()

    # Get payment milestones
    milestones = conn.execute("""
        SELECT * FROM payment_milestones WHERE quote_id = ? ORDER BY id
    """, (quote_id,)).fetchall()

    # Get project stages
    stages = conn.execute("""
        SELECT * FROM project_stages WHERE quote_id = ? ORDER BY stage_number
    """, (quote_id,)).fetchall()

    # Get delivery log
    delivery_log = conn.execute("""
        SELECT dl.*, u.name AS sent_by_name
        FROM delivery_log dl
        LEFT JOIN users u ON dl.sent_by = u.id
        WHERE dl.quote_id = ?
        ORDER BY dl.sent_at DESC
    """, (quote_id,)).fetchall()

    conn.close()

    return 200, {
        **dict(quote),
        'items': [dict(i) for i in items],
        'milestones': [dict(m) for m in milestones],
        'stages': [dict(s) for s in stages],
        'delivery_log': [dict(d) for d in delivery_log],
    }

def create_quotation(req):
    require_role(req, 'abc_staff')
    b = req['body']

    apartment_id = b.get('apartment_id')
    items = b.get('items', [])
    notes = b.get('notes', '').strip()

    if not apartment_id:
        raise ValueError('apartment_id is required')

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError('items array is required and must not be empty')

    conn = get_conn()

    # Verify apartment exists
    apt = conn.execute('SELECT id FROM apartments WHERE id = ?', (apartment_id,)).fetchone()
    if not apt:
        conn.close()
        raise ValueError('Apartment not found')

    c = conn.cursor()

    # Get next version for this apartment
    max_version = conn.execute("""
        SELECT MAX(version) as max_v FROM quotations WHERE apartment_id = ?
    """, (apartment_id,)).fetchone()

    next_version = (max_version['max_v'] or 0) + 1

    # Calculate total amount
    total_amount = 0
    for item in items:
        quantity = float(item.get('quantity', 1))
        unit_price = float(item.get('unit_price', 0))
        total_amount += quantity * unit_price

    # Insert quotation
    c.execute("""
        INSERT INTO quotations
            (apartment_id, version, generated_by, status, total_amount, notes)
        VALUES (?, ?, ?, 'draft', ?, ?)
    """, (apartment_id, next_version, req['user']['id'], total_amount, notes))

    quote_id = c.lastrowid

    # Insert quote items
    for item in items:
        item_name = item.get('item_name', '').strip()
        room = item.get('room', '').strip()
        description = item.get('description', '').strip()
        unit = item.get('unit', 'per unit').strip()
        quantity = float(item.get('quantity', 1))
        unit_price = float(item.get('unit_price', 0))
        labour_included = 1 if item.get('labour_included') else 0
        line_total = quantity * unit_price

        c.execute("""
            INSERT INTO quote_items
                (quote_id, item_name, room, description, unit, quantity, unit_price, labour_included, line_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quote_id, item_name, room, description, unit, quantity, unit_price, labour_included, line_total))

    # Create 3 payment milestones
    milestones_data = [
        ('advance', 50.0),
        ('on_delivery', 30.0),
        ('on_commissioning', 20.0),
    ]

    for stage, percentage in milestones_data:
        amount = (percentage / 100) * total_amount
        c.execute("""
            INSERT INTO payment_milestones (quote_id, stage, percentage, amount, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (quote_id, stage, percentage, amount))

    # Create 6 project stages
    stages_data = [
        (1, 'Drawings Issued'),
        (2, 'Materials Ordered'),
        (3, 'Materials Delivered on Site'),
        (4, 'Cabling Works'),
        (5, 'Installation & Programming'),
        (6, 'Commissioned & Handed Over'),
    ]

    for stage_number, stage_name in stages_data:
        c.execute("""
            INSERT INTO project_stages (quote_id, stage_number, stage_name, status)
            VALUES (?, ?, ?, 'pending')
        """, (quote_id, stage_number, stage_name))

    # Update viable requests for this apartment to 'quoted'
    c.execute("""
        UPDATE requests SET status = 'quoted'
        WHERE apartment_id = ? AND status = 'viable'
    """, (apartment_id,))

    conn.commit()
    conn.close()

    return 201, {'success': True, 'id': quote_id}

def update_quotation_status(req):
    require_role(req, 'abc_staff')
    quote_id = req['params']['id']
    b = req['body']

    status = b.get('status', '').strip()
    drop_reason = b.get('drop_reason', '').strip()

    if status not in ('draft', 'sent', 'confirmed', 'dropped'):
        raise ValueError('Invalid status')

    if status == 'dropped' and not drop_reason:
        raise ValueError('drop_reason is required when status is "dropped"')

    conn = get_conn()

    # Verify quote exists
    quote = conn.execute('SELECT id, apartment_id FROM quotations WHERE id = ?', (quote_id,)).fetchone()
    if not quote:
        conn.close()
        raise ValueError('Quotation not found')

    c = conn.cursor()

    # Update quotation status
    c.execute("""
        UPDATE quotations SET status = ?, drop_reason = ? WHERE id = ?
    """, (status, drop_reason if drop_reason else None, quote_id))

    # If confirmed, update quoted requests to 'confirmed'
    if status == 'confirmed':
        c.execute("""
            UPDATE requests SET status = 'confirmed'
            WHERE apartment_id = ? AND status = 'quoted'
        """, (quote['apartment_id'],))

    conn.commit()
    conn.close()

    return 200, {'success': True}

def generate_quote_pdf_handler(req):
    require_role(req, 'abc_staff')
    quote_id = req['params']['id']

    conn = get_conn()

    quote = conn.execute("""
        SELECT q.*, a.apartment_number, a.bedroom_type, a.owner_name
        FROM quotations q
        JOIN apartments a ON q.apartment_id = a.id
        WHERE q.id = ?
    """, (quote_id,)).fetchone()

    if not quote:
        conn.close()
        raise ValueError('Quotation not found')

    items = conn.execute("""
        SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id
    """, (quote_id,)).fetchall()

    milestones = conn.execute("""
        SELECT * FROM payment_milestones WHERE quote_id = ? ORDER BY id
    """, (quote_id,)).fetchall()

    conn.close()

    # Generate PDF
    pdf_path = generate_quote_pdf(dict(quote), [dict(i) for i in items], [dict(m) for m in milestones])

    # Save pdf_path to database
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE quotations SET pdf_path = ? WHERE id = ?', (pdf_path, quote_id))
    conn.commit()
    conn.close()

    return 200, {'success': True, 'pdf_path': pdf_path}

def get_quotation_pdf(req):
    require_auth(req)
    quote_id = req['params']['id']

    conn = get_conn()
    quote = conn.execute('SELECT pdf_path FROM quotations WHERE id = ?', (quote_id,)).fetchone()
    conn.close()

    if not quote or not quote['pdf_path']:
        raise ValueError('PDF not found')

    # Return file serving dict
    return 200, {
        '__file__': True,
        'path': quote['pdf_path'],
        'name': f'quotation_{quote_id}.pdf'
    }

def log_delivery(req):
    require_auth(req)
    quote_id = req['params']['id']
    b = req['body']

    channel = b.get('channel', '').strip()
    recipient = b.get('recipient', '').strip()

    if channel not in ('whatsapp', 'email', 'download'):
        raise ValueError('Invalid channel')

    if not recipient:
        raise ValueError('recipient is required')

    conn = get_conn()

    # Verify quote exists and get its status
    quote = conn.execute('SELECT id, status FROM quotations WHERE id = ?', (quote_id,)).fetchone()
    if not quote:
        conn.close()
        raise ValueError('Quotation not found')

    c = conn.cursor()

    # Insert delivery log
    c.execute("""
        INSERT INTO delivery_log (quote_id, sent_by, channel, recipient)
        VALUES (?, ?, ?, ?)
    """, (quote_id, req['user']['id'], channel, recipient))

    # If quote status is 'draft', update to 'sent'
    if quote['status'] == 'draft':
        c.execute('UPDATE quotations SET status = ? WHERE id = ?', ('sent', quote_id))

    conn.commit()
    conn.close()

    return 200, {'success': True}

quotation_routes = {
    ('GET',  '/api/quotations'):              list_quotations,
    ('GET',  '/api/quotations/<id>'):         get_quotation,
    ('POST', '/api/quotations'):              create_quotation,
    ('PATCH', '/api/quotations/<id>/status'): update_quotation_status,
    ('POST', '/api/quotations/<id>/pdf'):     generate_quote_pdf_handler,
    ('GET',  '/api/quotations/<id>/pdf-download'): get_quotation_pdf,
    ('POST', '/api/quotations/<id>/log-delivery'): log_delivery,
}
