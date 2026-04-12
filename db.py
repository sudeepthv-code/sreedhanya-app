import sqlite3
import os
import bcrypt

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'sreedhanya.db'))

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('sreedhanya_staff','abc_staff')),
            is_active INTEGER NOT NULL DEFAULT 1,
            last_login TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment_number TEXT UNIQUE NOT NULL,
            floor INTEGER,
            block TEXT,
            bedroom_type TEXT NOT NULL CHECK(bedroom_type IN ('2BHK','3BHK','4BHK')),
            owner_name TEXT,
            owner_phone TEXT,
            owner_email TEXT,
            status TEXT NOT NULL DEFAULT 'no_request'
                CHECK(status IN ('no_request','in_progress','completed')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS catalogue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            description TEXT,
            key_materials TEXT,
            default_unit TEXT NOT NULL DEFAULT 'per unit',
            default_unit_price REAL NOT NULL DEFAULT 0,
            labour_included INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_custom INTEGER NOT NULL DEFAULT 0,
            added_by INTEGER REFERENCES users(id),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment_id INTEGER NOT NULL REFERENCES apartments(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            room TEXT NOT NULL,
            catalogue_item_id INTEGER REFERENCES catalogue(id),
            custom_item_name TEXT,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending_review'
                CHECK(status IN ('pending_review','viable','not_viable','quoted','confirmed','dropped','in_progress','completed')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS viability_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL REFERENCES requests(id),
            reviewed_by INTEGER NOT NULL REFERENCES users(id),
            decision TEXT NOT NULL CHECK(decision IN ('viable','not_viable')),
            reason TEXT,
            reviewed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment_id INTEGER NOT NULL REFERENCES apartments(id),
            version INTEGER NOT NULL DEFAULT 1,
            generated_by INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','sent','confirmed','dropped')),
            drop_reason TEXT,
            total_amount REAL NOT NULL DEFAULT 0,
            pdf_path TEXT,
            notes TEXT,
            generated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quote_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
            item_name TEXT NOT NULL,
            room TEXT,
            description TEXT,
            unit TEXT NOT NULL DEFAULT 'per unit',
            quantity REAL NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL DEFAULT 0,
            labour_included INTEGER NOT NULL DEFAULT 0,
            line_total REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS payment_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL REFERENCES quotations(id),
            stage TEXT NOT NULL CHECK(stage IN ('advance','on_delivery','on_commissioning')),
            percentage REAL NOT NULL,
            amount REAL NOT NULL,
            due_trigger TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','received','overdue')),
            received_at TEXT,
            invoice_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS project_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL REFERENCES quotations(id),
            stage_number INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','in_progress','completed')),
            notes TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL REFERENCES quotations(id),
            milestone_id INTEGER NOT NULL REFERENCES payment_milestones(id),
            invoice_number TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            pdf_path TEXT,
            generated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS delivery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER REFERENCES quotations(id),
            invoice_id INTEGER REFERENCES invoices(id),
            sent_by INTEGER NOT NULL REFERENCES users(id),
            channel TEXT NOT NULL CHECK(channel IN ('whatsapp','email','download')),
            recipient TEXT,
            sent_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def seed_db():
    conn = get_conn()
    c = conn.cursor()

    # Default users
    pw_admin = bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode()
    pw_staff = bcrypt.hashpw(b'Staff@123', bcrypt.gensalt()).decode()
    c.execute("INSERT OR IGNORE INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
              ('Sudeepth (A+BC)', 'sudeepthv@gmail.com', pw_admin, 'abc_staff'))
    c.execute("INSERT OR IGNORE INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
              ('Sreedhanya Staff', 'staff@sreedhanyahomes.com', pw_staff, 'sreedhanya_staff'))

    # 92 Apartments across 3 blocks
    layout = [
        ('A', list(range(1,6)), [('01','2BHK'),('02','3BHK'),('03','3BHK'),('04','3BHK'),('05','4BHK'),('06','2BHK')]),
        ('B', list(range(1,6)), [('01','2BHK'),('02','3BHK'),('03','3BHK'),('04','3BHK'),('05','4BHK'),('06','3BHK')]),
        ('C', list(range(1,6)), [('01','3BHK'),('02','3BHK'),('03','3BHK'),('04','2BHK')]),
    ]
    apts = []
    for block, floors, flats in layout:
        for floor in floors:
            for num, bhk in flats:
                apts.append((f"{block}{floor}{num}", floor, block, bhk))

    # Pad to 92
    extra = 92 - len(apts)
    for i in range(extra):
        apts.append((f"D1{str(i+1).zfill(2)}", 1, 'D', '3BHK'))

    apts = apts[:92]
    c.executemany("INSERT OR IGNORE INTO apartments (apartment_number,floor,block,bedroom_type) VALUES (?,?,?,?)", apts)

    # Catalogue
    catalogue = [
        ('Switchboard Position Change',
         'Relocate a switchboard to a new position. Requires extra KNX cable, CAT6 cable and WAGO connectors.',
         'KNX cable (Rs.92/m), CAT6 cable (Rs.30/m), WAGO connectors (Rs.150 each)', 'per room', 0, 0),
        ('Additional ON/OFF Lights/Fans (up to 3 circuits per room)',
         'Bring additional light/fan circuits on to automation. Max 3 extra circuits per room.',
         'Letour 3CH ON/OFF + 6CH Binary Input', 'per module', 0, 0),
        ('Geyser Automation',
         'Schedule or remotely switch on geyser before reaching home.',
         'Letour 3CH ON/OFF + 6CH Binary Input, Electric Contactor', 'per unit', 0, 0),
        ('AC Integration',
         'Full AC control (on/off, temperature, mode) from the automation app.',
         'AC Control Unit', 'per indoor unit', 0, 0),
        ('Door Magnetic Sensor',
         'Notification when main door or balcony door opens. Ideal for NRI clients.',
         'Wireless Door Magnetic Sensor', 'per door', 0, 0),
        ('Curtain Motor & Track',
         'Automate curtains/blinds. Schedule open/close times.',
         'Curtain Motor, Track, KNX cable', 'per curtain', 0, 0),
        ('Additional Dimming Circuits (up to 2 per room)',
         'Extra dimming circuits on automation. Dimmable lights required from lighting vendor.',
         'Letour 2CH Analog (1-10) Dimmer', 'per module', 0, 0),
        ('Irrigation Module',
         'Automate watering for vertical gardens or potted plants.',
         'Letour 3CH ON/OFF + 6CH Binary Input, Solenoid Valves, KNX cable', 'per zone', 0, 0),
        ('Wi-Fi CCTV Camera',
         'Monitor who enters/leaves the apartment. Wi-Fi based.',
         'Wi-Fi CCTV Camera, Memory Card', 'per camera', 0, 0),
        ('Wi-Fi Access Point',
         'Stable Wi-Fi coverage throughout apartment.',
         '4-Channel POE Switch, Wireless Access Point', 'per unit', 0, 0),
        ('Customised Keypads',
         'Replace mechanical switchboards with automation keypads. Metal or glass finish.',
         'Automation Keypad (metal or glass)', 'per keypad', 0, 0),
        ('Multi-Room Audio System',
         'Zone-wise audio. Play same or different tracks in each room via Airplay/Spotify.',
         'Zone Amplifier, Speakers, Speaker Cabling', 'per zone', 0, 0),
        ('AV Integration (Smart TV / Soundbar)',
         'Control Smart TV and Soundbar from automation app. Enable movie scenes.',
         'AV Control Module', 'per device', 0, 0),
        ('Scene Creation / UI Changes',
         'Custom scenes and UI changes to automation app. Charged per session.',
         'Service only', 'per session', 2500, 1),
        ('KNX Cable', 'KNX cable for routing. Labour excluded.',
         'KNX Cable 1x2x0.8mm HF 300V', 'per metre', 92, 0),
        ('CAT6 Cable', 'CAT6 cable for interconnecting switch boxes. Labour excluded.',
         'CAT6 Cable', 'per metre', 30, 0),
        ('WAGO Connector', 'WAGO connector for joining KNX cables.',
         'WAGO Connector', 'per unit', 150, 0),
    ]
    c.executemany("""
        INSERT OR IGNORE INTO catalogue
            (item_name, description, key_materials, default_unit, default_unit_price, labour_included)
        VALUES (?,?,?,?,?,?)
    """, catalogue)

    conn.commit()
    conn.close()
    print("✅ Database seeded successfully")
    print("━" * 45)
    print("Default credentials:")
    print("  A+BC Staff:       sudeepthv@gmail.com  /  Admin@123")
    print("  Sreedhanya Staff: staff@sreedhanyahomes.com  /  Staff@123")
    print("━" * 45)

if __name__ == '__main__':
    init_db()
    seed_db()
