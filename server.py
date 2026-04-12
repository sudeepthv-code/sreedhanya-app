#!/usr/bin/env python3
"""
Sreedhanya AI Customisation App — Python Backend
Run: python server.py
"""
import json, os, re, sys, traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import jwt as pyjwt
import bcrypt

from db import init_db, get_conn
from routes.auth import auth_routes
from routes.apartments import apartment_routes
from routes.catalogue import catalogue_routes
from routes.requests import request_routes
from routes.quotations import quotation_routes
from routes.payments import payment_routes
from routes.stages import stage_routes
from routes.users import user_routes

JWT_SECRET  = os.environ.get('JWT_SECRET', 'sreedhanya-secret-change-in-production')
STATIC_DIR  = os.path.join(os.path.dirname(__file__), 'static')
PORT        = int(os.environ.get('PORT', 8080))
# On Railway: set PDF_STORAGE_DIR=/data/pdfs to serve from persistent volume
PDF_DIR     = os.environ.get('PDF_STORAGE_DIR', os.path.join(STATIC_DIR, 'pdfs'))

# Merge all routes
ALL_ROUTES = {}
for group in [auth_routes, apartment_routes, catalogue_routes, request_routes,
              quotation_routes, payment_routes, stage_routes, user_routes]:
    ALL_ROUTES.update(group)


def match_route(method, path):
    """Match URL path against route patterns, extract params."""
    for (route_method, pattern), handler in ALL_ROUTES.items():
        if route_method != method:
            continue
        regex = re.sub(r'<(\w+)>', r'(?P<\1>[^/]+)', pattern)
        m = re.fullmatch(regex, path)
        if m:
            return handler, m.groupdict()
    return None, {}


def get_current_user(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        conn = get_conn()
        user = conn.execute(
            'SELECT id, name, email, role, is_active FROM users WHERE id = ?', (payload['id'],)
        ).fetchone()
        conn.close()
        if user and user['is_active']:
            return dict(user)
        return None
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path} → {args[1] if len(args) > 1 else ''}")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath, filename, mime='application/pdf'):
        with open(filepath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, msg, status=400):
        self.send_json({'error': msg}, status)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def handle_request(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        # Serve frontend
        if path == '' or path == '/':
            index = os.path.join(STATIC_DIR, 'index.html')
            if os.path.exists(index):
                with open(index, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error_json('Frontend not built', 404)
            return

        # Health check
        if path == '/api/health':
            self.send_json({'status': 'ok', 'time': datetime.now(timezone.utc).isoformat()})
            return

        # Read body
        body = {}
        if method in ('POST', 'PUT', 'PATCH'):
            length = int(self.headers.get('Content-Length', 0))
            if length:
                try:
                    body = json.loads(self.rfile.read(length))
                except Exception:
                    body = {}

        # Auth
        current_user = get_current_user(self.headers.get('Authorization'))

        # Serve PDF files
        if path.startswith('/api/pdfs/'):
            filename = path[len('/api/pdfs/'):]
            filepath = os.path.join(PDF_DIR, filename)
            if os.path.exists(filepath) and current_user:
                self.send_file(filepath, filename)
            else:
                self.send_error_json('Not found', 404)
            return

        # Route matching
        handler, params = match_route(method, path)
        if handler is None:
            self.send_error_json(f'Route not found: {method} {path}', 404)
            return

        req = {
            'method': method,
            'path': path,
            'params': params,
            'query': {k: v[0] if len(v) == 1 else v for k, v in query.items()},
            'body': body,
            'user': current_user,
            'jwt_secret': JWT_SECRET,
        }

        try:
            status, data = handler(req)
            if isinstance(data, dict) and data.get('__file__'):
                self.send_file(data['path'], data['name'])
            else:
                self.send_json(data, status)
        except PermissionError as e:
            self.send_error_json(str(e), 403)
        except ValueError as e:
            self.send_error_json(str(e), 400)
        except Exception:
            traceback.print_exc()
            self.send_error_json('Internal server error', 500)

    def do_GET(self):    self.handle_request('GET')
    def do_POST(self):   self.handle_request('POST')
    def do_PUT(self):    self.handle_request('PUT')
    def do_PATCH(self):  self.handle_request('PATCH')
    def do_DELETE(self): self.handle_request('DELETE')


if __name__ == '__main__':
    print("🌱 Initialising database...")
    init_db()

    # Auto-seed if empty
    conn = get_conn()
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    if count == 0:
        from db import seed_db
        seed_db()

    print(f"🚀 Sreedhanya App running at http://localhost:{PORT}")
    print(f"   Open http://localhost:{PORT} in your browser\n")
    HTTPServer(('', PORT), Handler).serve_forever()
