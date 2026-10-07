import psycopg2
import streamlit as st

def init_db():
    # Connect directly to your free Neon Cloud Database
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    c = conn.cursor()
    
    # 1. Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')
    
    # Create default users if the table is empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (email, password, role) VALUES ('admin@company.com', 'admin123', 'Admin')")
        c.execute("INSERT INTO users (email, password, role) VALUES ('sales@company.com', 'sales123', 'Sales')")
        c.execute("INSERT INTO users (email, password, role) VALUES ('purchase@company.com', 'purchase123', 'Purchase')")
    
    # 2. Master Tables
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (id SERIAL PRIMARY KEY, name TEXT NOT NULL, contact TEXT, address TEXT, gstin TEXT, pan TEXT, bank_details TEXT, payment_terms TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (id SERIAL PRIMARY KEY, name TEXT NOT NULL, contact TEXT, address TEXT, gstin TEXT, credit_limit REAL, credit_days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT, hsn_code TEXT, tax_rate REAL, default_price REAL)''')
    
    # 3. Purchase Tables (All tracking columns included fresh)
    c.execute('''CREATE TABLE IF NOT EXISTS po_master (po_id SERIAL PRIMARY KEY, po_number TEXT NOT NULL, vendor_id INTEGER, po_date TEXT, total_amount REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS po_items (item_id SERIAL PRIMARY KEY, po_id INTEGER, product_id INTEGER, qty REAL, rate REAL, gst_amount REAL, total REAL, received_qty REAL DEFAULT 0, grn_qty REAL DEFAULT 0)''')
        
    # 4. Sales Tables
    c.execute('''CREATE TABLE IF NOT EXISTS so_master (so_id SERIAL PRIMARY KEY, so_number TEXT NOT NULL, client_id INTEGER, so_date TEXT, delivery_date TEXT, total_amount REAL, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS so_items (item_id SERIAL PRIMARY KEY, so_id INTEGER, product_id INTEGER, qty REAL, rate REAL, gst_amount REAL, total REAL, dispatch_qty REAL DEFAULT 0, received_qty REAL DEFAULT 0, rejected_qty REAL DEFAULT 0)''')

    # 5. Inventory & Finance
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_ledger (ledger_id SERIAL PRIMARY KEY, product_id INTEGER, batch_no TEXT, qty_in REAL DEFAULT 0, qty_out REAL DEFAULT 0, ref_type TEXT, ref_id TEXT, txn_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, party_type TEXT, party_id INTEGER, amount REAL, payment_mode TEXT, txn_date TEXT, notes TEXT, order_no TEXT, utr_number TEXT)''')
    
    # 6. Logistics
    c.execute('''CREATE TABLE IF NOT EXISTS logistics (id SERIAL PRIMARY KEY, order_ref TEXT, from_loc TEXT, to_loc TEXT, vehicle_no TEXT, driver_name TEXT, distance_km REAL, freight_cost REAL)''')
    
    conn.commit()
    conn.close()