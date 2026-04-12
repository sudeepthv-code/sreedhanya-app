from datetime import datetime
from db import get_conn
from routes.auth import require_auth, require_role
from services.pdf import generate_invoice_pdf

def list_payments(req):
    require_auth(req)
    quote_id = req['query'].get('quote_id')

    if not quote_id:
        raise ValueError('quote_id query parameter is required')

    conn = get_conn()

    milestones = conn.execute("""
        SELECT pm.* FROM payment_milestones pm
        WHERE pm.quote_id = ?
        ORDER BY pm.id
    """, (quote_id,)).fetchall()

    conn.close()

    return 200, [dict(m) for m in milestones]

def mark_payment_received(req):
    require_role(req, 'abc_staff')
    milestone_id = req['params']['id']

    conn = get_conn()

    milestone = conn.execute(
        'SELECT id FROM payment_milestones WHERE id = ?',
        (milestone_id,)
    ).fetchone()

    if not milestone:
        conn.close()
        raise ValueError('Payment milestone not found')

    c = conn.cursor()
    c.execute("""
        UPDATE payment_milestones
        SET status = 'received', received_at = datetime('now')
        WHERE id = ?
    """, (milestone_id,))

    conn.commit()
    conn.close()

    return 200, {'success': True}

def create_invoice(req):
    require_role(req, 'abc_staff')
    milestone_id = req['params']['id']

    conn = get_conn()

    # Get milestone with joins
    milestone = conn.execute("""
        SELECT pm.*, q.id as quote_id, a.apartment_number, a.owner_name
        FROM payment_milestones pm
        JOIN quotations q ON pm.quote_id = q.id
        JOIN apartments a ON q.apartment_id = a.id
        WHERE pm.id = ?
    """, (milestone_id,)).fetchone()

    if not milestone:
        conn.close()
        raise ValueError('Payment milestone not found')

    # Generate invoice number
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    stage_upper = milestone['stage'].upper()
    invoice_number = f"INV-{milestone['apartment_number']}-{stage_upper}-{timestamp}"

    # Generate invoice PDF
    pdf_path = generate_invoice_pdf(dict(milestone), invoice_number)

    # Insert invoice into database
    c = conn.cursor()
    c.execute("""
        INSERT INTO invoices (quote_id, milestone_id, invoice_number, amount, pdf_path)
        VALUES (?, ?, ?, ?, ?)
    """, (milestone['quote_id'], milestone_id, invoice_number, milestone['amount'], pdf_path))

    invoice_id = c.lastrowid

    # Update milestone with invoice_id
    c.execute(
        'UPDATE payment_milestones SET invoice_id = ? WHERE id = ?',
        (invoice_id, milestone_id)
    )

    conn.commit()
    conn.close()

    return 201, {'success': True, 'invoice_id': invoice_id, 'invoice_number': invoice_number}

payment_routes = {
    ('GET',  '/api/payments'):                 list_payments,
    ('PATCH', '/api/payments/<id>/received'):  mark_payment_received,
    ('POST', '/api/payments/<id>/invoice'):    create_invoice,
}
