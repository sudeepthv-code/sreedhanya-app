# Sreedhanya AI Customisation App

A web application for managing apartment customisation requests across the Sreedhanya AI project (92 apartments).

---

## Requirements

- **Python 3.8+** — if not installed, download from https://www.python.org/downloads/
- The following Python packages (install once):

**On Mac / Linux:**
```bash
pip3 install bcrypt PyJWT reportlab
```

**On Windows:**
```bash
pip install bcrypt PyJWT reportlab
```

That's it. No Node.js, no npm, no database server needed.

---

## Running the App

**On Mac / Linux:**
```bash
# Navigate to this folder
cd python_backend

# First time only — install packages
pip3 install bcrypt PyJWT reportlab

# Start the server
python3 server.py
```

**On Windows:**
```bash
cd python_backend
pip install bcrypt PyJWT reportlab
python server.py
```

Then open **http://localhost:5000** in your browser.

The database is created and seeded automatically on first run.

---

## Default Login Credentials

| Role | Email | Password |
|------|-------|----------|
| A+BC Staff (admin) | sudeepthv@gmail.com | Admin@123 |
| Sreedhanya Staff | staff@sreedhanyahomes.com | Staff@123 |

**Change these passwords immediately after first login** (User Management → Edit User).

---

## App Structure

```
python_backend/
├── server.py          # HTTP server & router (run this)
├── db.py              # SQLite schema & seed data
├── routes/            # API route handlers
│   ├── auth.py        # Login
│   ├── apartments.py  # 92 apartments
│   ├── catalogue.py   # Customisation catalogue
│   ├── requests.py    # Customisation requests
│   ├── quotations.py  # Quote generation
│   ├── payments.py    # Payment milestones
│   ├── stages.py      # Project stages
│   └── users.py       # User management
├── services/
│   └── pdf.py         # Quote & invoice PDF generation
├── static/
│   ├── index.html     # React frontend (served by Python)
│   └── pdfs/          # Generated PDF files stored here
└── sreedhanya.db      # SQLite database (auto-created)
```

---

## Changing the Port

```bash
PORT=8080 python server.py
```

---

## Deploying to Railway.app

1. Create a free account at https://railway.app
2. Create a new project → "Deploy from GitHub repo"
3. Push this folder to a GitHub repository
4. Railway will detect Python and run `python server.py`
5. Set environment variable: `JWT_SECRET=your-very-long-random-secret-key`

---

## Workflow Summary

1. **Sreedhanya staff** logs in → selects apartment → logs customisation requests
2. **A+BC staff** reviews requests for viability
3. **A+BC staff** builds a quotation from viable requests → generates PDF
4. **Sreedhanya staff** shares PDF with end client → records client response
5. On confirmation, **A+BC staff** tracks: payment milestones → project stages → invoices
