from datetime import datetime
from db import get_conn
from routes.auth import require_auth, require_role

def list_stages(req):
    require_auth(req)
    quote_id = req['query'].get('quote_id')

    if not quote_id:
        raise ValueError('quote_id query parameter is required')

    conn = get_conn()

    stages = conn.execute("""
        SELECT * FROM project_stages
        WHERE quote_id = ?
        ORDER BY stage_number
    """, (quote_id,)).fetchall()

    conn.close()

    return 200, [dict(s) for s in stages]

def update_stage(req):
    require_role(req, 'abc_staff')
    stage_id = req['params']['id']
    b = req['body']

    status = b.get('status', '').strip()
    notes = b.get('notes', '').strip()

    if status not in ('pending', 'in_progress', 'completed'):
        raise ValueError('Invalid status')

    conn = get_conn()

    # Get stage with quote_id
    stage = conn.execute("""
        SELECT id, quote_id FROM project_stages WHERE id = ?
    """, (stage_id,)).fetchone()

    if not stage:
        conn.close()
        raise ValueError('Project stage not found')

    c = conn.cursor()

    # Update stage
    if status == 'completed':
        c.execute("""
            UPDATE project_stages
            SET status = ?, notes = ?, completed_at = datetime('now')
            WHERE id = ?
        """, (status, notes if notes else None, stage_id))
    else:
        c.execute("""
            UPDATE project_stages
            SET status = ?, notes = ?
            WHERE id = ?
        """, (status, notes if notes else None, stage_id))

    # Check if all stages for this quote_id are completed
    all_stages = conn.execute("""
        SELECT COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
        FROM project_stages WHERE quote_id = ?
    """, (stage['quote_id'],)).fetchone()

    if all_stages['total'] == all_stages['completed']:
        # All stages completed, update apartment status to 'completed'
        quote = conn.execute("""
            SELECT apartment_id FROM quotations WHERE id = ?
        """, (stage['quote_id'],)).fetchone()

        if quote:
            c.execute(
                "UPDATE apartments SET status = 'completed' WHERE id = ?",
                (quote['apartment_id'],)
            )

    conn.commit()
    conn.close()

    return 200, {'success': True}

stage_routes = {
    ('GET',  '/api/stages'):     list_stages,
    ('PATCH', '/api/stages/<id>'): update_stage,
}
