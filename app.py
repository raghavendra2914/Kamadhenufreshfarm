import streamlit as st
import pandas as pd
import psycopg2
import time
import datetime
import platform
import warnings
import streamlit.components.v1 as components
import plotly.express as px
import streamlit_antd_components as sac
from database import init_db

warnings.filterwarnings('ignore')

init_db()

def get_db_connection(): return psycopg2.connect(st.secrets["DATABASE_URL"])

# Auto-update database tables dynamically
try:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("ALTER TABLE vendors ADD COLUMN IF NOT EXISTS bank_account VARCHAR(100);")
    c.execute("ALTER TABLE vendors ADD COLUMN IF NOT EXISTS ifsc_code VARCHAR(50);")
    c.execute("ALTER TABLE vendors ADD COLUMN IF NOT EXISTS passbook_file BYTEA;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            location TEXT,
            facility_type VARCHAR(100),
            capacity NUMERIC,
            incharge_name VARCHAR(100),
            contact VARCHAR(50)
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            emp_name VARCHAR(200),
            role VARCHAR(100),
            salary_per_day NUMERIC,
            join_date DATE,
            status VARCHAR(50) DEFAULT 'Active'
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_expenses (
            id SERIAL PRIMARY KEY,
            order_ref VARCHAR(100),
            expense_type VARCHAR(100),
            amount NUMERIC,
            notes TEXT,
            logged_date DATE
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS wastage_ledger (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            batch_no VARCHAR(100),
            qty NUMERIC,
            reason TEXT,
            log_date DATE
        );
    """)
    conn.commit()
    conn.close()
except Exception:
    pass

def recalculate_order_totals(order_type, order_id):
    conn = get_db_connection()
    c = conn.cursor()
    if order_type == 'PO':
        c.execute("SELECT COALESCE(SUM(total), 0) FROM po_items WHERE po_id = %s", (order_id,))
        new_total = float(c.fetchone()[0])
        c.execute("UPDATE po_master SET total_amount = %s WHERE po_id = %s", (new_total, order_id))
    else:
        c.execute("SELECT COALESCE(SUM(total), 0) FROM so_items WHERE so_id = %s", (order_id,))
        new_total = float(c.fetchone()[0])
        c.execute("UPDATE so_master SET total_amount = %s WHERE so_id = %s", (new_total, order_id))
    conn.commit()
    conn.close()

st.set_page_config(page_title="Company ERP", layout="wide")

# ==========================================
# LOGIN SYSTEM
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""

if not st.session_state.logged_in:
    st.markdown("""
        <style>
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); color: #2e7d32; }
            100% { transform: scale(1); }
        }
        .animated-title {
            text-align: center;
            font-family: 'Arial Black', sans-serif;
            animation: pulse 3s infinite;
        }
        </style>
        <h1 class="animated-title">🌱 Kamadhenufreshfarm ERP</h1>
        <br>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Domain Email ID")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT role FROM users WHERE email = %s AND password = %s", (email, password))
            result = c.fetchone()
            conn.close()
            
            if result:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_role = result[0]
                st.balloons()  
                time.sleep(1.5) 
                st.rerun()
            else:
                st.error("Invalid Email or Password. Please try again.")
    st.stop()

# ==========================================
# MAIN ERP APP (ANT DESIGN NAVIGATION)
# ==========================================
with st.sidebar:
    st.title(f"Welcome, {st.session_state.user_role}")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    st.markdown("---")
    
    if st.session_state.user_role == "Admin":
        menu_items = [
            sac.MenuItem('Dashboard', icon='speedometer2'),
            sac.MenuItem('Master Data', icon='database', children=[
                sac.MenuItem('Vendor Onboarding', icon='person-plus'),
                sac.MenuItem('Client Onboarding', icon='person-badge'),
                sac.MenuItem('Product Master', icon='box'),
                sac.MenuItem('Facility Onboarding', icon='building')
            ]),
            sac.MenuItem('HR & Payroll', icon='people', children=[
                sac.MenuItem('Employee Master', icon='person-vcard')
            ]),
            sac.MenuItem('Purchase', icon='cart3', children=[
                sac.MenuItem('Create PO', icon='cart-plus'),
                sac.MenuItem('PO Records & GRN', icon='receipt-cutoff'),
                sac.MenuItem('View Purchase Orders', icon='table'),
                sac.MenuItem('Purchase Forecasting', icon='graph-up')
            ]),
            sac.MenuItem('Sales', icon='graph-up-arrow', children=[
                sac.MenuItem('Create Sales Order', icon='cart-check'),
                sac.MenuItem('Sales Records & Tracking', icon='truck-flatbed'),
                sac.MenuItem('View Sales Orders', icon='table')
            ]),
            sac.MenuItem('Inventory', icon='box-seam', children=[
                sac.MenuItem('Live Stock', icon='boxes'),
                sac.MenuItem('Ledger History', icon='clock-history'),
                sac.MenuItem('Log Wastage & Spoilage', icon='trash3')
            ]),
            sac.MenuItem('Finance', icon='bank', children=[
                sac.MenuItem('Add Payment', icon='cash-coin'),
                sac.MenuItem('Receivables (Client Bills)', icon='graph-up'),
                sac.MenuItem('Payables (Vendor Bills)', icon='graph-down'),
                sac.MenuItem('Payment Records', icon='journal-text')
            ]),
            sac.MenuItem('Logistics & Ops', icon='truck', children=[
                sac.MenuItem('Add PO/SO Expenses', icon='currency-rupee'),
                sac.MenuItem('Add Dispatch Details', icon='send'),
                sac.MenuItem('Route & Freight Report', icon='map')
            ]),
            sac.MenuItem('System Info', icon='info-circle')
        ]
    else:
        menu_items = [
            sac.MenuItem('Dashboard', icon='speedometer2'),
            sac.MenuItem('Sales', icon='graph-up-arrow', children=[
                sac.MenuItem('Create Sales Order', icon='cart-check'),
                sac.MenuItem('Sales Records & Tracking', icon='truck-flatbed')
            ])
        ]

    selected_item = sac.menu(menu_items, format_func='title', open_all=False, size='md', variant='filled', color='#2e7d32')

parent_map = {
    'Vendor Onboarding': 'Master Data', 'Client Onboarding': 'Master Data', 'Product Master': 'Master Data', 'Facility Onboarding': 'Master Data',
    'Employee Master': 'HR & Payroll',
    'Create PO': 'Purchase', 'PO Records & GRN': 'Purchase', 'View Purchase Orders': 'Purchase', 'Purchase Forecasting': 'Purchase',
    'Create Sales Order': 'Sales', 'Sales Records & Tracking': 'Sales', 'View Sales Orders': 'Sales',
    'Live Stock': 'Inventory', 'Ledger History': 'Inventory', 'Log Wastage & Spoilage': 'Inventory',
    'Add Payment': 'Finance', 'Receivables (Client Bills)': 'Finance', 'Payables (Vendor Bills)': 'Finance', 'Payment Records': 'Finance',
    'Add PO/SO Expenses': 'Logistics & Ops', 'Add Dispatch Details': 'Logistics & Ops', 'Route & Freight Report': 'Logistics & Ops',
    'Dashboard': 'Dashboard', 'System Info': 'System Info'
}

if selected_item in ['Master Data', 'HR & Payroll', 'Purchase', 'Sales', 'Inventory', 'Finance', 'Logistics & Ops']:
    defaults = {'Master Data': 'Vendor Onboarding', 'HR & Payroll': 'Employee Master', 'Purchase': 'Create PO', 'Sales': 'Create Sales Order', 'Inventory': 'Live Stock', 'Finance': 'Add Payment', 'Logistics & Ops': 'Add PO/SO Expenses'}
    sub_menu = defaults[selected_item]
    main_menu = selected_item
else:
    main_menu = parent_map.get(selected_item, selected_item)
    sub_menu = selected_item

def show_data_with_delete(table_name, df, id_prefix):
    if df.empty:
        st.info("No records found.")
        return
    cols = df.columns.tolist()
    layout = [1] * len(cols) + [1]
    header_cols = st.columns(layout)
    for i, col_name in enumerate(cols):
        display_name = "ID" if col_name == "id" else col_name.upper()
        header_cols[i].markdown(f"**{display_name}**")
    header_cols[-1].markdown("**ACTION**")
    st.markdown("---")
    for index, row in df.iterrows():
        row_cols = st.columns(layout)
        for i, col_name in enumerate(cols):
            if col_name == "id": row_cols[i].write(f"{id_prefix}{int(row[col_name]):03d}")
            else: row_cols[i].write(row[col_name])
        if st.session_state.user_role == "Admin":
            if row_cols[-1].button("🗑️ Delete", key=f"del_{table_name}_{row['id']}"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(f"DELETE FROM {table_name} WHERE id = %s", (int(row['id']),))
                conn.commit()
                conn.close()
                st.rerun()
        else:
            row_cols[-1].write("🔒 Read Only")

# ==========================================
# 1. MASTER DATA 
# ==========================================
if main_menu == "Master Data":
    if sub_menu == "Vendor Onboarding":
        st.header("Vendor Master")
        with st.form("vendor_form"):
            c1, c2 = st.columns(2)
            v_name = c1.text_input("Vendor Name *")
            v_contact = c2.text_input("Contact Number")
            v_gstin = c1.text_input("GSTIN")
            v_pan = c2.text_input("PAN")
            v_address = st.text_area("Full Address")
            v_terms = st.text_input("Payment Terms")
            
            st.markdown("### 🏦 Secure Bank Details")
            c3, c4 = st.columns(2)
            bank_acc1 = c3.text_input("Account Number *", type="password")
            bank_acc2 = c4.text_input("Confirm Account Number *")
            v_ifsc = c3.text_input("IFSC Code *")
            v_file = st.file_uploader("Upload Cancelled Cheque / Passbook Image", type=["pdf", "jpg", "jpeg", "png"])
            
            if st.form_submit_button("Save Vendor"):
                if not v_name or not bank_acc1 or not bank_acc2 or not v_ifsc:
                    st.error("Please fill all mandatory (*) fields including Bank details.")
                elif bank_acc1 != bank_acc2:
                    st.error("Account Numbers do not match! Please check again.")
                else:
                    file_data = psycopg2.Binary(v_file.read()) if v_file else None
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO vendors (name, contact, address, gstin, pan, payment_terms, bank_account, ifsc_code, passbook_file) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                              (str(v_name), str(v_contact), str(v_address), str(v_gstin), str(v_pan), str(v_terms), str(bank_acc1), str(v_ifsc), file_data))
                    conn.commit()
                    conn.close()
                    st.success("Vendor and Bank details securely saved!")
                    time.sleep(1.5)
                    st.rerun()
                    
        st.subheader("Registered Vendors")
        conn = get_db_connection()
        show_data_with_delete("vendors", pd.read_sql_query("SELECT id, name, contact, gstin, bank_account as \"A/C No\" FROM vendors", conn), "V")
        conn.close()
        
    elif sub_menu == "Facility Onboarding":
        st.header("🏢 Facility Master")
        with st.form("facility_form"):
            c1, c2 = st.columns(2)
            f_name = c1.text_input("Facility Name * (e.g. HSR Hub, Farm 1)")
            f_type = c2.selectbox("Facility Type", ["Warehouse", "Processing Unit", "Cold Storage", "Retail Outlet", "Farm", "Other"])
            f_loc = st.text_area("Full Location Address *")
            if st.form_submit_button("Save Facility"):
                if f_name and f_loc:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO facilities (name, location, facility_type) VALUES (%s, %s, %s)", (str(f_name), str(f_loc), str(f_type)))
                    conn.commit()
                    conn.close()
                    st.success("Facility securely saved!")
                    time.sleep(1)
                    st.rerun()
        st.subheader("Registered Facilities")
        conn = get_db_connection()
        fac_df = pd.read_sql_query('SELECT id, name as "Facility", facility_type as "Type", location as "Address" FROM facilities', conn)
        show_data_with_delete("facilities", fac_df, "FAC-")
        conn.close()
        
    elif sub_menu == "Client Onboarding":
        st.header("Client Master")
        with st.form("client_form"):
            c1, c2 = st.columns(2)
            c_name = c1.text_input("Client Name *")
            c_contact = c2.text_input("Contact Number")
            c_gstin = c1.text_input("GSTIN")
            c_limit = c2.number_input("Credit Limit (Rs)", min_value=0.0, step=1000.0)
            if st.form_submit_button("Save Client"):
                if c_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO clients (name, contact, gstin, credit_limit) VALUES (%s, %s, %s, %s)", (str(c_name), str(c_contact), str(c_gstin), float(c_limit)))
                    conn.commit()
                    conn.close()
                    st.success("Client saved!")
                    st.rerun()
        st.subheader("Registered Clients")
        conn = get_db_connection()
        show_data_with_delete("clients", pd.read_sql_query("SELECT id, name, contact, gstin, credit_limit FROM clients", conn), "S-")
        conn.close()
        
    elif sub_menu == "Product Master":
        st.header("Product Master")
        with st.form("product_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Product Name *")
            p_cat = c2.selectbox("Category", ["Fruits", "Vegetables", "Other"])
            p_hsn = c1.text_input("HSN Code")
            p_tax = c2.selectbox("GST Rate (%)", [0.0, 5.0, 12.0, 18.0])
            p_price = st.number_input("Default Selling Price (Rs)", min_value=0.0)
            if st.form_submit_button("Save Product"):
                if p_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO products (name, category, hsn_code, tax_rate, default_price) VALUES (%s, %s, %s, %s, %s)", (str(p_name), str(p_cat), str(p_hsn), float(p_tax), float(p_price)))
                    conn.commit()
                    conn.close()
                    st.success("Product saved!")
                    st.rerun()
        st.subheader("Product List")
        conn = get_db_connection()
        show_data_with_delete("products", pd.read_sql_query("SELECT id, name, category, default_price FROM products", conn), "SKU")
        conn.close()

# ==========================================
# HR & PAYROLL MODULE
# ==========================================
elif main_menu == "HR & Payroll":
    if sub_menu == "Employee Master":
        st.header("👷 Employee Master (Payroll Tracking)")
        with st.form("emp_form"):
            c1, c2 = st.columns(2)
            e_name = c1.text_input("Employee Name *")
            e_role = c2.selectbox("Role / Designation", ["Farm Worker", "Driver", "Manager", "Admin", "Sales Rep", "Other"])
            e_salary = c1.number_input("Salary / Wages (Per Day) *", min_value=0.0, step=50.0)
            e_join = c2.date_input("Join Date")
            if st.form_submit_button("Save Employee"):
                if e_name and e_salary >= 0:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO employees (emp_name, role, salary_per_day, join_date) VALUES (%s, %s, %s, %s)", (str(e_name), str(e_role), float(e_salary), str(e_join)))
                    conn.commit()
                    conn.close()
                    st.success("Employee saved!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Name and Salary are required.")
                    
        st.subheader("Active Employees")
        conn = get_db_connection()
        show_data_with_delete("employees", pd.read_sql_query('SELECT id, emp_name as "Name", role as "Designation", salary_per_day as "Daily Wage (Rs)" FROM employees', conn), "EMP-")
        conn.close()

# ==========================================
# 2. PURCHASE MODULE
# ==========================================
elif main_menu == "Purchase":
    if sub_menu == "Create PO":
        st.header("Punch Purchase Order")
        if 'po_cart' not in st.session_state: st.session_state.po_cart = []
        conn = get_db_connection()
        vendors = pd.read_sql_query("SELECT id, name FROM vendors", conn)
        products = pd.read_sql_query("SELECT id, name, tax_rate FROM products", conn)
        facilities = pd.read_sql_query("SELECT id, name FROM facilities", conn)
        conn.close()
        
        if vendors.empty or products.empty: st.warning("⚠️ Please add Master Data first.")
        else:
            col1, col2, col3 = st.columns(3)
            vendor_dict = {row['id']: f"V{int(row['id']):03d} - {row['name']}" for _, row in vendors.iterrows()}
            fac_list = ["Default Warehouse"] + facilities['name'].tolist() if not facilities.empty else ["Default Warehouse"]
            
            selected_vendor_id = col1.selectbox("Select Vendor", options=list(vendor_dict.keys()), format_func=lambda x: vendor_dict[x])
            selected_facility = col2.selectbox("Receiving Facility", fac_list)
            po_date = col3.date_input("PO Date")
            st.divider()
            
            with st.form("add_item_form"):
                c1, c2, c3 = st.columns(3)
                prod_dict = {row['id']: f"SKU{int(row['id']):03d} - {row['name']} ({row['tax_rate']}% GST)" for _, row in products.iterrows()}
                selected_prod_id = c1.selectbox("Select Product", options=list(prod_dict.keys()), format_func=lambda x: prod_dict[x])
                qty = c2.number_input("Indent Quantity (Ordered)", min_value=1.0, value=1.0, step=1.0)
                rate = c3.number_input("Rate per unit (Rs)", min_value=0.0, step=1.0)
                if st.form_submit_button("➕ Click to Add Item"):
                    tax_rate = float(products.loc[products['id'] == selected_prod_id, 'tax_rate'].values[0])
                    base_total = float(qty * rate)
                    gst_amount = float(base_total * (tax_rate / 100))
                    
                    st.session_state.po_cart.append({
                        "prod_id": int(selected_prod_id), 
                        "Product": str(prod_dict[selected_prod_id]), 
                        "Indent Qty": float(qty), 
                        "Rate": float(rate), 
                        "GST Rs": float(gst_amount), 
                        "Total Rs": float(base_total + gst_amount)
                    })
                    st.success("Item added successfully!")
            
            if len(st.session_state.po_cart) > 0:
                cart_df = pd.DataFrame(st.session_state.po_cart)
                st.dataframe(cart_df.drop(columns=['prod_id']), use_container_width=True, hide_index=True)
                if st.button("💾 Save Purchase Order", type="primary"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM po_master")
                    po_number = f"PO-{(c.fetchone()[0] + 1):04d}"
                    grand_total = float(cart_df['Total Rs'].sum())
                    
                    c.execute("INSERT INTO po_master (po_number, vendor_id, po_date, total_amount, status) VALUES (%s, %s, %s, %s, %s) RETURNING po_id", (str(po_number), int(selected_vendor_id), str(po_date), grand_total, "Ordered"))
                    new_po_id = int(c.fetchone()[0])
                    
                    for item in st.session_state.po_cart:
                        c.execute("INSERT INTO po_items (po_id, product_id, qty, rate, gst_amount, total) VALUES (%s, %s, %s, %s, %s, %s)", 
                                  (new_po_id, int(item['prod_id']), float(item['Indent Qty']), float(item['Rate']), float(item['GST Rs']), float(item['Total Rs'])))
                        c.execute("INSERT INTO inventory_ledger (product_id, batch_no, qty_in, qty_out, ref_type, ref_id, txn_date) VALUES (%s, %s, %s, 0, 'Purchase', %s, %s)", 
                                  (int(item['prod_id']), f"BATCH-{po_number}", float(item['Indent Qty']), str(po_number), str(po_date)))
                    conn.commit()
                    conn.close()
                    st.session_state.po_cart = []
                    st.success(f"Generated {po_number} at {selected_facility}!")
                    time.sleep(1)
                    st.rerun()

    elif sub_menu == "PO Records & GRN":
        st.header("Update & Delete Purchase Order Items (GRN)")
        conn = get_db_connection()
        orders_query = "SELECT p.po_id, p.po_number, p.po_date, v.name as party_name FROM po_master p JOIN vendors v ON p.vendor_id = v.id ORDER BY p.po_id DESC"
        pos = pd.read_sql_query(orders_query, conn)
        if not pos.empty:
            order_dict = {row['po_number']: f"{row['po_number']} | {row['party_name']} | {row['po_date']}" for _, row in pos.iterrows()}
            selected_po = st.selectbox("Select Purchase Order to Update", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
            po_id = int(pos.loc[pos['po_number'] == selected_po, 'po_id'].values[0])
            st.write("---")
            
            items_query = f'SELECT item_id, p.id as prod_id, p.name as "Product", qty as "Indent_Qty", COALESCE(received_qty, qty) as "Received_Qty", COALESCE(grn_qty, qty) as "GRN_Qty", rate as "Rate" FROM po_items i JOIN products p ON i.product_id = p.id WHERE po_id = {po_id}'
            items_df = pd.read_sql_query(items_query, conn)
            
            if items_df.empty:
                st.warning("No items remaining in this Purchase Order.")
            else:
                for idx, row in items_df.iterrows():
                    item_id = int(row['item_id'])
                    prod_id = int(row['prod_id'])
                    
                    with st.form(key=f"po_item_form_{item_id}"):
                        st.markdown(f"**📦 {row['Product']}** *(Ordered: {row['Indent_Qty']})*")
                        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
                        new_rec = c1.number_input("Received Qty", value=float(row['Received_Qty']), step=1.0, key=f"f_rec_{item_id}")
                        new_grn = c2.number_input("GRN Qty", value=float(row['GRN_Qty']), step=1.0, key=f"f_grn_{item_id}")
                        new_rate = c3.number_input("Rate (Rs)", value=float(row['Rate']), step=0.01, format="%.2f", key=f"f_rt_{item_id}")
                        
                        btn_c1, btn_c2 = c4.columns(2)
                        save_btn = btn_c1.form_submit_button("✏️ Save Rate & Qty")
                        del_btn = btn_c2.form_submit_button("🗑️ Delete Item")
                        
                        if save_btn:
                            c = conn.cursor()
                            c.execute("SELECT tax_rate FROM products WHERE id = %s", (prod_id,))
                            tax_rate = float(c.fetchone()[0])
                            base_total = new_grn * new_rate
                            gst_amount = base_total * (tax_rate / 100)
                            item_total = base_total + gst_amount
                            
                            c.execute("UPDATE po_items SET received_qty = %s, grn_qty = %s, rate = %s, gst_amount = %s, total = %s WHERE item_id = %s", 
                                      (new_rec, new_grn, new_rate, gst_amount, item_total, item_id))
                            c.execute("UPDATE inventory_ledger SET qty_in = %s WHERE ref_type = 'Purchase' AND ref_id = %s AND product_id = %s", 
                                      (new_grn, str(selected_po), prod_id))
                            conn.commit()
                            recalculate_order_totals('PO', po_id)
                            st.success(f"Updated! Rate set to ₹{new_rate:.2f}, Total: ₹{item_total:,.2f}")
                            time.sleep(1)
                            st.rerun()
                            
                        if del_btn:
                            c = conn.cursor()
                            c.execute("DELETE FROM po_items WHERE item_id = %s", (item_id,))
                            c.execute("DELETE FROM inventory_ledger WHERE ref_type = 'Purchase' AND ref_id = %s AND product_id = %s", (str(selected_po), prod_id))
                            conn.commit()
                            recalculate_order_totals('PO', po_id)
                            st.warning("Item completely deleted from PO and Inventory!")
                            time.sleep(1)
                            st.rerun()
        conn.close()

    elif sub_menu == "View Purchase Orders":
        st.header("📋 View & Export Purchase Orders (True Landing Cost)")
        conn = get_db_connection()
        col1, col2, col3 = st.columns(3)
        start_date = col1.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
        end_date = col2.date_input("End Date", datetime.date.today())
        
        vendors_df = pd.read_sql_query("SELECT name FROM vendors", conn)
        vendor_list = ["All Vendors"] + vendors_df['name'].tolist()
        selected_vendor = col3.selectbox("Filter by Vendor", vendor_list)
        
        query = """
            SELECT 
                p.po_number as "PO Number", 
                p.po_date as "Date", 
                v.name as "Vendor", 
                p.total_amount as "Product Total (Rs)", 
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = p.po_number AND expense_type = 'Freight'), 0) as "Logistics (Rs)",
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = p.po_number AND expense_type = 'Labour'), 0) as "Labour Charges (Rs)",
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = p.po_number AND expense_type = 'Other'), 0) as "Other Expenses (Rs)",
                (p.total_amount + COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = p.po_number), 0)) as "True Landing Cost (Rs)"
            FROM po_master p 
            JOIN vendors v ON p.vendor_id = v.id 
            WHERE p.po_date BETWEEN %s AND %s
        """
        params = [str(start_date), str(end_date)]
        if selected_vendor != "All Vendors":
            query += " AND v.name = %s"
            params.append(selected_vendor)
        query += " ORDER BY p.po_id DESC"
        
        po_df = pd.read_sql_query(query, conn, params=params)
        
        if po_df.empty:
            st.info("No Purchase Orders found.")
        else:
            st.dataframe(po_df, use_container_width=True, hide_index=True)
            csv = po_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download List as CSV", data=csv, file_name="Purchase_Orders.csv", mime="text/csv", type="primary")
            
            st.divider()
            st.subheader("🔍 View PO Detailed Items")
            selected_po_view = st.selectbox("Select a PO Number to view inside details", po_df["PO Number"].tolist())
            if selected_po_view:
                items_query = """
                SELECT pr.name as "Product", i.qty as "Indent Qty", i.grn_qty as "GRN Qty", i.rate as "Rate (Rs)", i.total as "Total Amount (Rs)" 
                FROM po_items i JOIN products pr ON i.product_id = pr.id JOIN po_master p ON i.po_id = p.po_id WHERE p.po_number = %s
                """
                items_df = pd.read_sql_query(items_query, conn, params=[selected_po_view])
                st.write(f"**Items inside {selected_po_view}:**")
                st.dataframe(items_df, use_container_width=True, hide_index=True)
        conn.close()
        
    elif sub_menu == "Purchase Forecasting":
        st.header("🔮 Purchase Forecasting & Demand Analysis")
        st.write("This engine analyzes historical order velocities and client ordering patterns to predict 7-day purchasing needs and daily demand breakdown.")
        
        conn = get_db_connection()
        thirty_days_ago = str(datetime.date.today() - datetime.timedelta(days=30))
        
        forecast_query = f"""
            WITH sales_data AS (
                SELECT i.product_id, SUM(i.qty) as total_sold
                FROM so_items i
                JOIN so_master s ON i.so_id = s.so_id
                WHERE s.so_date >= '{thirty_days_ago}'
                GROUP BY i.product_id
            ),
            stock_data AS (
                SELECT product_id, SUM(qty_in) - SUM(qty_out) as current_stock
                FROM inventory_ledger
                GROUP BY product_id
            )
            SELECT 
                p.name as "Product",
                ROUND(CAST(COALESCE(sd.total_sold, 0) AS NUMERIC), 2) as "Sold (Last 30 Days)",
                ROUND(CAST(COALESCE(sd.total_sold, 0) / 30.0 AS NUMERIC), 2) as "Daily Avg Run Rate",
                ROUND(CAST(CEIL(COALESCE(sd.total_sold, 0) / 30.0 * 7) AS NUMERIC), 2) as "7-Day Forecast Qty",
                ROUND(CAST(COALESCE(st.current_stock, 0) AS NUMERIC), 2) as "Current Live Stock",
                ROUND(CAST(GREATEST(0, CEIL(COALESCE(sd.total_sold, 0) / 30.0 * 7) - COALESCE(st.current_stock, 0)) AS NUMERIC), 2) as "Suggested Order Qty"
            FROM products p
            LEFT JOIN sales_data sd ON p.id = sd.product_id
            LEFT JOIN stock_data st ON p.id = st.product_id
            WHERE COALESCE(sd.total_sold, 0) > 0 OR COALESCE(st.current_stock, 0) > 0
            ORDER BY "Suggested Order Qty" DESC
        """
        
        forecast_df = pd.read_sql_query(forecast_query, conn)
        
        if forecast_df.empty:
            st.info("Not enough sales data in the last 30 days to generate a forecast.")
        else:
            def highlight_orders(val):
                if val > 0: return 'background-color: #ffebee; color: #c62828; font-weight: bold'
                return 'background-color: #e8f5e9; color: #2e7d32'
                
            styled_df = forecast_df.style.map(highlight_orders, subset=["Suggested Order Qty"])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📅 Client & SKU Wise Day-of-Week Forecast (Mon - Sun)")
            st.caption("Average quantity ordered per day based on historical purchasing patterns across specific weekdays.")
            
            daywise_query = """
                SELECT 
                    c.name as "Client",
                    p.name as "Product",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 1 THEN i.qty END) AS NUMERIC), 2) as "Mon",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 2 THEN i.qty END) AS NUMERIC), 2) as "Tue",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 3 THEN i.qty END) AS NUMERIC), 2) as "Wed",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 4 THEN i.qty END) AS NUMERIC), 2) as "Thu",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 5 THEN i.qty END) AS NUMERIC), 2) as "Fri",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 6 THEN i.qty END) AS NUMERIC), 2) as "Sat",
                    ROUND(CAST(AVG(CASE WHEN EXTRACT(ISODOW FROM CAST(s.so_date AS DATE)) = 7 THEN i.qty END) AS NUMERIC), 2) as "Sun",
                    ROUND(CAST(SUM(i.qty) AS NUMERIC), 2) as "Total Sold"
                FROM so_items i
                JOIN so_master s ON i.so_id = s.so_id
                JOIN clients c ON s.client_id = c.id
                JOIN products p ON i.product_id = p.id
                GROUP BY c.name, p.name
                ORDER BY c.name, "Total Sold" DESC
            """
            daywise_df = pd.read_sql_query(daywise_query, conn)
            
            if daywise_df.empty:
                st.info("No client sales history found to build day-wise matrix.")
            else:
                daywise_df = daywise_df.fillna(0.0)
                st.dataframe(daywise_df, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("📊 Suggested Purchase Quantities")
            chart_df = forecast_df[forecast_df["Suggested Order Qty"] > 0]
            if not chart_df.empty:
                fig = px.bar(chart_df, x="Product", y="Suggested Order Qty", 
                             title="Restock Priority For This Week", 
                             color="Suggested Order Qty", 
                             color_continuous_scale="Reds")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("🎉 You have sufficient inventory for all items for the next 7 days based on current run rates!")
                
        conn.close()

# ==========================================
# 3. SALES MODULE (BATCH TRACKING ENABLED)
# ==========================================
elif main_menu == "Sales":
    if sub_menu == "Create Sales Order":
        st.header("Punch Sales Order (From Specific PO Batches)")
        if 'so_cart' not in st.session_state: st.session_state.so_cart = []
        conn = get_db_connection()
        clients = pd.read_sql_query("SELECT id, name FROM clients", conn)
        products = pd.read_sql_query("SELECT id, name, tax_rate, default_price FROM products", conn)
        
        if not clients.empty and not products.empty:
            col1, col2, col3 = st.columns(3)
            client_dict = {row['id']: f"S-{int(row['id']):03d} - {row['name']}" for _, row in clients.iterrows()}
            selected_client_id = col1.selectbox("Select Client", options=list(client_dict.keys()), format_func=lambda x: client_dict[x])
            so_date = col2.date_input("Sales Date")
            delivery_date = col3.date_input("Delivery Date")
            st.divider()
            
            with st.form("add_so_item_form"):
                st.markdown("#### 1. Select Product")
                prod_dict = {row['id']: f"SKU{int(row['id']):03d} - {row['name']} ({row['tax_rate']}% GST)" for _, row in products.iterrows()}
                selected_prod_id = st.selectbox("Select Product", options=list(prod_dict.keys()), format_func=lambda x: prod_dict[x])
                
                c = conn.cursor()
                c.execute("""
                    SELECT 
                        i.batch_no, 
                        SUM(i.qty_in) - SUM(i.qty_out) as available_qty, 
                        v.name as vendor_name, 
                        pi.rate as avg_cost
                    FROM inventory_ledger i
                    LEFT JOIN po_master pm ON i.batch_no = 'BATCH-' || pm.po_number
                    LEFT JOIN vendors v ON pm.vendor_id = v.id
                    LEFT JOIN po_items pi ON pm.po_id = pi.po_id AND i.product_id = pi.product_id
                    WHERE i.product_id = %s AND i.batch_no LIKE 'BATCH-%%'
                    GROUP BY i.batch_no, v.name, pi.rate
                    HAVING SUM(i.qty_in) - SUM(i.qty_out) > 0
                """, (int(selected_prod_id),))
                available_batches = c.fetchall()
                
                st.markdown("#### 2. Select Vendor Supply Batch")
                if not available_batches:
                    st.error("❌ No stock available from any Vendor for this product. Punch a Purchase Order first.")
                    batch_selected = None
                else:
                    batch_dict = {b[0]: f"{b[0]} | Vendor: {b[2]} | Available: {b[1]} | PO Rate: ₹{b[3]}" for b in available_batches}
                    batch_selected = st.selectbox("Link to specific Vendor Supply Batch", options=list(batch_dict.keys()), format_func=lambda x: batch_dict[x])
                    max_available = next((float(b[1]) for b in available_batches if b[0] == batch_selected), 1.0)
                    
                    c1, c2 = st.columns(2)
                    suggested_price = float(products.loc[products['id'] == selected_prod_id, 'default_price'].values[0])
                    qty = c1.number_input("Order Quantity", min_value=1.0, max_value=float(max_available), value=1.0, step=1.0)
                    rate = c2.number_input("Selling Rate per unit (Rs)", min_value=0.0, value=float(suggested_price), step=10.0)
                    
                if st.form_submit_button("➕ Click to Add Item") and batch_selected:
                    tax_rate = float(products.loc[products['id'] == selected_prod_id, 'tax_rate'].values[0])
                    base_total = float(qty * rate)
                    gst_amount = float(base_total * (tax_rate / 100))
                    
                    st.session_state.so_cart.append({
                        "prod_id": int(selected_prod_id), 
                        "Product": str(prod_dict[selected_prod_id]),
                        "Batch Ref": str(batch_selected),
                        "Order Qty": float(qty), 
                        "Rate": float(rate), 
                        "GST Rs": float(gst_amount), 
                        "Total Rs": float(base_total + gst_amount)
                    })
                    st.success("Item added successfully!")
            
            if len(st.session_state.so_cart) > 0:
                cart_df = pd.DataFrame(st.session_state.so_cart)
                st.dataframe(cart_df.drop(columns=['prod_id']), use_container_width=True, hide_index=True)
                if st.button("💾 Save Sales Order", type="primary"):
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM so_master")
                    so_number = f"SO-{(c.fetchone()[0] + 1):04d}"
                    grand_total = float(cart_df['Total Rs'].sum())
                    
                    c.execute("INSERT INTO so_master (so_number, client_id, so_date, delivery_date, total_amount, status) VALUES (%s, %s, %s, %s, %s, %s) RETURNING so_id", (str(so_number), int(selected_client_id), str(so_date), str(delivery_date), grand_total, "Pending"))
                    new_so_id = int(c.fetchone()[0])
                    
                    for item in st.session_state.so_cart:
                        c.execute("INSERT INTO so_items (so_id, product_id, qty, rate, gst_amount, total) VALUES (%s, %s, %s, %s, %s, %s)", 
                                  (new_so_id, int(item['prod_id']), float(item['Order Qty']), float(item['Rate']), float(item['GST Rs']), float(item['Total Rs'])))
                        c.execute("INSERT INTO inventory_ledger (product_id, batch_no, qty_in, qty_out, ref_type, ref_id, txn_date) VALUES (%s, %s, 0, %s, 'Sale', %s, %s)", 
                                  (int(item['prod_id']), str(item['Batch Ref']), float(item['Order Qty']), str(so_number), str(so_date)))
                    conn.commit()
                    conn.close()
                    st.session_state.so_cart = []
                    st.success(f"Generated {so_number} linked to Vendor Batches!")
                    time.sleep(1)
                    st.rerun()
        conn.close()

    elif sub_menu == "Sales Records & Tracking":
        st.header("Update & Delete Sales Order Items (Dispatch)")
        conn = get_db_connection()
        orders_query = "SELECT s.so_id, s.so_number, s.so_date, c.name as party_name FROM so_master s JOIN clients c ON s.client_id = c.id ORDER BY s.so_id DESC"
        sos = pd.read_sql_query(orders_query, conn)
        if not sos.empty:
            order_dict = {row['so_number']: f"{row['so_number']} | {row['party_name']} | {row['so_date']}" for _, row in sos.iterrows()}
            selected_so = st.selectbox("Select Sales Order to Update", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
            so_id = int(sos.loc[sos['so_number'] == selected_so, 'so_id'].values[0])
            st.write("---")
            
            items_query = f'SELECT item_id, p.id as prod_id, p.name as "Product", qty as "Order_Qty", COALESCE(dispatch_qty, qty) as "Dispatch_Qty", COALESCE(received_qty, qty) as "Client_Received_Qty", COALESCE(rejected_qty, 0) as "Rejected_Qty", rate as "Rate" FROM so_items i JOIN products p ON i.product_id = p.id WHERE so_id = {so_id}'
            items_df = pd.read_sql_query(items_query, conn)
            
            if items_df.empty:
                st.warning("No items remaining in this Sales Order.")
            else:
                for idx, row in items_df.iterrows():
                    item_id = int(row['item_id'])
                    prod_id = int(row['prod_id'])
                    
                    with st.form(key=f"so_item_form_{item_id}"):
                        st.markdown(f"**📦 {row['Product']}** *(Ordered: {row['Order_Qty']})*")
                        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
                        new_disp = c1.number_input("Dispatch Qty", value=float(row['Dispatch_Qty']), step=1.0, key=f"f_disp_{item_id}")
                        new_rec = c2.number_input("Client Rec Qty", value=float(row['Client_Received_Qty']), step=1.0, key=f"f_srec_{item_id}")
                        new_rej = c3.number_input("Rejected Qty", value=float(row['Rejected_Qty']), step=1.0, key=f"f_srej_{item_id}")
                        
                        btn_c1, btn_c2 = c4.columns(2)
                        save_btn = btn_c1.form_submit_button("✏️ Save Dispatch")
                        del_btn = btn_c2.form_submit_button("🗑️ Delete Item")
                        
                        if save_btn:
                            c = conn.cursor()
                            rate = float(row['Rate'])
                            c.execute("SELECT tax_rate FROM products WHERE id = %s", (prod_id,))
                            tax_rate = float(c.fetchone()[0])
                            
                            base_total = new_rec * rate
                            gst_amount = base_total * (tax_rate / 100)
                            item_total = base_total + gst_amount
                            
                            c.execute("UPDATE so_items SET dispatch_qty = %s, received_qty = %s, rejected_qty = %s, gst_amount = %s, total = %s WHERE item_id = %s", 
                                      (new_disp, new_rec, new_rej, gst_amount, item_total, item_id))
                            c.execute("UPDATE inventory_ledger SET qty_out = %s WHERE ref_type = 'Sale' AND ref_id = %s AND product_id = %s", 
                                      (new_rec, str(selected_so), prod_id))
                            conn.commit()
                            recalculate_order_totals('SO', so_id)
                            st.success(f"Updated! Client Received: {new_rec}, Total: ₹{item_total:,.2f}")
                            time.sleep(1)
                            st.rerun()
                            
                        if del_btn:
                            c = conn.cursor()
                            c.execute("DELETE FROM so_items WHERE item_id = %s", (item_id,))
                            c.execute("DELETE FROM inventory_ledger WHERE ref_type = 'Sale' AND ref_id = %s AND product_id = %s", (str(selected_so), prod_id))
                            conn.commit()
                            recalculate_order_totals('SO', so_id)
                            st.warning("Item completely deleted from SO and Inventory!")
                            time.sleep(1)
                            st.rerun()
        conn.close()

    elif sub_menu == "View Sales Orders":
        st.header("📋 View & Export Sales Orders")
        conn = get_db_connection()
        col1, col2, col3 = st.columns(3)
        start_date = col1.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
        end_date = col2.date_input("End Date", datetime.date.today())
        
        clients_df = pd.read_sql_query("SELECT name FROM clients", conn)
        client_list = ["All Clients"] + clients_df['name'].tolist()
        selected_client = col3.selectbox("Filter by Client", client_list)
        
        query = """
            SELECT 
                s.so_number as "SO Number", 
                s.so_date as "Date", 
                c.name as "Client", 
                s.total_amount as "Order Total (Rs)", 
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = s.so_number AND expense_type = 'Freight'), 0) as "Logistics (Rs)",
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = s.so_number AND expense_type = 'Labour'), 0) as "Labour Charges (Rs)",
                COALESCE((SELECT SUM(amount) FROM order_expenses WHERE order_ref = s.so_number AND expense_type = 'Other'), 0) as "Other Expenses (Rs)",
                s.status as "Status" 
            FROM so_master s 
            JOIN clients c ON s.client_id = c.id 
            WHERE s.so_date BETWEEN %s AND %s
        """
        params = [str(start_date), str(end_date)]
        if selected_client != "All Clients":
            query += " AND c.name = %s"
            params.append(selected_client)
        query += " ORDER BY s.so_id DESC"
        
        so_df = pd.read_sql_query(query, conn, params=params)
        
        if so_df.empty:
            st.info("No Sales Orders found.")
        else:
            st.dataframe(so_df, use_container_width=True, hide_index=True)
            csv = so_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download List as CSV", data=csv, file_name="Sales_Orders.csv", mime="text/csv", type="primary")
            
            st.divider()
            st.subheader("🔍 View SO Detailed Items")
            selected_so_view = st.selectbox("Select a SO Number to view inside details", so_df["SO Number"].tolist())
            if selected_so_view:
                items_query = """
                SELECT p.name as "Product", i.qty as "Order Qty", i.received_qty as "Client Received Qty", i.rate as "Rate (Rs)", i.total as "Total Amount (Rs)" 
                FROM so_items i JOIN products p ON i.product_id = p.id JOIN so_master s ON i.so_id = s.so_id WHERE s.so_number = %s
                """
                items_df = pd.read_sql_query(items_query, conn, params=[selected_so_view])
                st.write(f"**Items inside {selected_so_view}:**")
                st.dataframe(items_df, use_container_width=True, hide_index=True)
        conn.close()

# ==========================================
# 4. INVENTORY & WASTAGE MODULE
# ==========================================
elif main_menu == "Inventory":
    if sub_menu == "Live Stock":
        st.header("📦 Live Stock Tracker (Batch Wise)")
        conn = get_db_connection()
        stock_df = pd.read_sql_query('SELECT p.id as "SKU ID", p.name as "Product Name", i.batch_no as "Batch Ref", COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) as "Current Stock" FROM products p LEFT JOIN inventory_ledger i ON p.id = i.product_id GROUP BY p.id, p.name, i.batch_no HAVING COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) > 0', conn)
        if not stock_df.empty:
            stock_df['SKU ID'] = stock_df['SKU ID'].apply(lambda x: f"SKU{int(x):03d}")
            st.dataframe(stock_df, use_container_width=True, hide_index=True)
        else:
            st.info("No active stock available.")
        conn.close()
        
    elif sub_menu == "Log Wastage & Spoilage":
        st.header("🗑️ Log Stock Wastage")
        st.write("Write off spoiled inventory directly against the Vendor's PO Batch to ensure accurate P&L.")
        conn = get_db_connection()
        stock_df = pd.read_sql_query('SELECT p.id, p.name, i.batch_no, COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) as available_qty FROM products p JOIN inventory_ledger i ON p.id = i.product_id GROUP BY p.id, p.name, i.batch_no HAVING COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) > 0', conn)
        
        if stock_df.empty:
            st.info("No stock available to write off.")
        else:
            with st.form("wastage_form"):
                batch_dict = {f"{row['id']}_{row['batch_no']}": f"{row['name']} | Batch: {row['batch_no']} | Available: {row['available_qty']}" for _, row in stock_df.iterrows()}
                selected_val = st.selectbox("Select Product Batch", options=list(batch_dict.keys()), format_func=lambda x: batch_dict[x])
                
                c1, c2 = st.columns(2)
                w_qty = c1.number_input("Wastage Quantity to Write-Off", min_value=1.0, step=1.0)
                w_reason = c2.selectbox("Reason", ["Transit Damage", "Rot / Spoilage", "Quality Rejection", "Lost/Stolen"])
                
                if st.form_submit_button("Write Off Stock"):
                    prod_id, batch_no = selected_val.split("_")
                    c = conn.cursor()
                    
                    c.execute("INSERT INTO wastage_ledger (product_id, batch_no, qty, reason, log_date) VALUES (%s, %s, %s, %s, %s)", 
                              (int(prod_id), str(batch_no), float(w_qty), str(w_reason), str(datetime.date.today())))
                    c.execute("INSERT INTO inventory_ledger (product_id, batch_no, qty_in, qty_out, ref_type, ref_id, txn_date) VALUES (%s, %s, 0, %s, 'Wastage', 'WRITE-OFF', %s)", 
                              (int(prod_id), str(batch_no), float(w_qty), str(datetime.date.today())))
                              
                    conn.commit()
                    st.success(f"Wastage recorded! {w_qty} units written off.")
                    time.sleep(1)
                    st.rerun()
        conn.close()
        
    elif sub_menu == "Ledger History":
        st.header("Inventory Ledger")
        conn = get_db_connection()
        ledger_df = pd.read_sql_query('SELECT i.txn_date as "Date", p.name as "Product", i.batch_no as "Batch Ref", i.ref_type as "Type", i.ref_id as "Reference", i.qty_in as "Qty IN", i.qty_out as "Qty OUT" FROM inventory_ledger i JOIN products p ON i.product_id = p.id ORDER BY i.ledger_id DESC', conn)
        if not ledger_df.empty: st.dataframe(ledger_df, use_container_width=True, hide_index=True)
        conn.close()

# ==========================================
# 5. FINANCE MODULE (AGING REPORT)
# ==========================================
elif main_menu == "Finance":
    
    def style_aging_row(row):
        if row['Balance (Rs)'] <= 0.01:
            style = 'background-color: #e8f5e9; color: #2e7d32' 
        elif row['Days Outstanding'] > 30:
            style = 'background-color: #ffebee; color: #c62828' 
        elif row['Days Outstanding'] > 15:
            style = 'background-color: #fff3e0; color: #e65100' 
        else:
            style = '' 
        return [style] * len(row)

    if sub_menu == "Add Payment":
        st.header("💸 Record Order-Wise Payment")
        party_type = st.radio("Who are you transacting with?", ["Client (Receiving Money)", "Vendor (Paying Money)"])
        conn = get_db_connection()
        if "Client" in party_type:
            parties = pd.read_sql_query("SELECT id, name FROM clients", conn)
            db_party_type = "Client"
            prefix = "S-"
        else:
            parties = pd.read_sql_query("SELECT id, name FROM vendors", conn)
            db_party_type = "Vendor"
            prefix = "V"
            
        if parties.empty: st.warning(f"No {db_party_type}s found.")
        else:
            party_dict = {row['id']: f"{prefix}{int(row['id']):03d} - {row['name']}" for _, row in parties.iterrows()}
            selected_party = st.selectbox("Select Party", options=list(party_dict.keys()), format_func=lambda x: party_dict[x])
            if db_party_type == "Vendor":
                orders_query = f"SELECT p.po_number as order_no, ROUND(CAST(p.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = p.po_number), 0) AS NUMERIC), 2) as pending_amount FROM po_master p WHERE p.vendor_id = {selected_party} AND ROUND(CAST(p.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = p.po_number), 0) AS NUMERIC), 2) > 0.01"
            else:
                orders_query = f"SELECT s.so_number as order_no, ROUND(CAST(s.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = s.so_number), 0) AS NUMERIC), 2) as pending_amount FROM so_master s WHERE s.client_id = {selected_party} AND ROUND(CAST(s.total_amount - COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = s.so_number), 0) AS NUMERIC), 2) > 0.01"
            orders_df = pd.read_sql_query(orders_query, conn)
            if orders_df.empty:
                st.success(f"✅ All bills for {party_dict[selected_party]} are fully paid!")
            else:
                st.info(f"📌 Found {len(orders_df)} unpaid bill(s) remaining for {party_dict[selected_party]}.")
                col1, col2 = st.columns(2)
                order_list = orders_df['order_no'].tolist()
                selected_order = col1.selectbox("Select Pending Bill/Order to Pay", order_list)
                pending_amount = orders_df.loc[orders_df['order_no'] == selected_order, 'pending_amount'].values[0]
                pay_date = col2.date_input("Payment Date", datetime.date.today())
                amount = col1.number_input("Amount (Rs)", min_value=0.0, value=float(pending_amount), step=10.0)
                pay_mode = col2.selectbox("Payment Mode", ["UPI", "Bank Transfer (NEFT/RTGS)", "Cash", "Cheque"])
                utr_no = col1.text_input("UTR / Transaction Ref Number *")
                notes = col2.text_input("Notes")
                if st.button("💾 Save & Mark as Paid", type="primary"):
                    if utr_no or pay_mode == "Cash":
                        c = conn.cursor()
                        c.execute("INSERT INTO payments (party_type, party_id, order_no, amount, payment_mode, utr_number, txn_date, notes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (str(db_party_type), int(selected_party), str(selected_order), float(amount), str(pay_mode), str(utr_no), str(pay_date), str(notes)))
                        conn.commit()
                        st.success(f"✅ SUCCESS! Payment of Rs {amount} saved for {selected_order}.")
                        time.sleep(1.5)
                        st.rerun()
                    else: st.error("UTR / Reference number is required for Bank/UPI transactions.")
        conn.close()
                    
    elif sub_menu == "Receivables (Client Bills)":
        st.header("📈 Client Receivables (Aging Report)")
        st.caption("🟢 **Paid** | ⚪ **Under 15 Days** | 🟠 **15-30 Days Overdue** | 🔴 **30+ Days Overdue**")
        conn = get_db_connection()
        query = 'SELECT s.so_number as "Sales Order", c.name as "Client", s.so_date as "Date", s.total_amount as "Bill Amount (Rs)", COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = s.so_number), 0) as "Paid Amount (Rs)" FROM so_master s JOIN clients c ON s.client_id = c.id ORDER BY s.so_id DESC'
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df['Balance (Rs)'] = (df['Bill Amount (Rs)'] - df['Paid Amount (Rs)']).astype(float).round(2)
            df['Status'] = df['Balance (Rs)'].apply(lambda x: '✅ Paid' if x <= 0.01 else '⏳ Pending')
            
            today = pd.Timestamp(datetime.date.today())
            df['Days Outstanding'] = (today - pd.to_datetime(df['Date'])).dt.days
            
            utr_df = pd.read_sql_query("SELECT order_no, string_agg(utr_number, ', ') as UTRs FROM payments GROUP BY order_no", conn)
            df = df.merge(utr_df, left_on='Sales Order', right_on='order_no', how='left').drop(columns=['order_no'])
            df['UTRs'] = df['utrs'].fillna('-')
            df.drop(columns=['utrs'], inplace=True, errors='ignore')
            
            styled_df = df.style.apply(style_aging_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Aging Report as CSV", data=csv, file_name="Client_Receivables.csv", mime="text/csv", type="primary")
            
            st.divider()
            st.subheader("✏️ Manage Payments & Orders")
            st.write("Edit or delete existing payments below. To edit the actual Bill Amount, go to **Sales -> Sales Records & Tracking**.")
            
            selected_so = st.selectbox("Select Sales Order to Manage Payments", df['Sales Order'].tolist())
            if selected_so:
                pay_query = "SELECT id, txn_date, payment_mode, amount FROM payments WHERE order_no = %s"
                pay_df = pd.read_sql_query(pay_query, conn, params=[selected_so])
                
                if pay_df.empty:
                    st.info(f"No payments found for {selected_so}.")
                else:
                    for idx, row in pay_df.iterrows():
                        pay_id = row['id']
                        with st.form(key=f"rec_pay_{pay_id}"):
                            st.write(f"**Payment Date:** {row['txn_date']} | **Mode:** {row['payment_mode']}")
                            c1, c2, c3 = st.columns([2, 1, 1])
                            new_amt = c1.number_input("Paid Amount (Rs)", value=float(row['amount']), step=100.0, key=f"amt_{pay_id}")
                            
                            save_btn = c2.form_submit_button("💾 Update")
                            del_btn = c3.form_submit_button("🗑️ Delete")
                            
                            if save_btn:
                                c = conn.cursor()
                                c.execute("UPDATE payments SET amount = %s WHERE id = %s", (new_amt, pay_id))
                                conn.commit()
                                st.success("Payment Updated!")
                                time.sleep(1)
                                st.rerun()
                                
                            if del_btn:
                                c = conn.cursor()
                                c.execute("DELETE FROM payments WHERE id = %s", (pay_id,))
                                conn.commit()
                                st.warning("Payment Deleted!")
                                time.sleep(1)
                                st.rerun()
                                
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("⚠️ Danger Zone: Delete Entire Order"):
                    st.warning(f"This will permanently delete {selected_so}, including all its items, inventory ledgers, and payments.")
                    if st.button("🗑️ Confirm Delete Order", key=f"del_so_{selected_so}"):
                        c = conn.cursor()
                        c.execute("SELECT so_id FROM so_master WHERE so_number = %s", (selected_so,))
                        res = c.fetchone()
                        if res:
                            so_id_del = res[0]
                            c.execute("DELETE FROM so_items WHERE so_id = %s", (so_id_del,))
                            c.execute("DELETE FROM inventory_ledger WHERE ref_type = 'Sale' AND ref_id = %s", (selected_so,))
                            c.execute("DELETE FROM order_expenses WHERE order_ref = %s", (selected_so,))
                            c.execute("DELETE FROM logistics WHERE order_ref = %s", (selected_so,))
                            c.execute("DELETE FROM payments WHERE order_no = %s", (selected_so,))
                            c.execute("DELETE FROM so_master WHERE so_id = %s", (so_id_del,))
                            conn.commit()
                            st.success(f"{selected_so} completely deleted!")
                            time.sleep(1.5)
                            st.rerun()
        else: st.info("No Sales Orders found.")
        conn.close()
            
    elif sub_menu == "Payables (Vendor Bills)":
        st.header("📉 Vendor Payables (Aging Report)")
        st.caption("🟢 **Paid** | ⚪ **Under 15 Days** | 🟠 **15-30 Days Overdue** | 🔴 **30+ Days Overdue**")
        conn = get_db_connection()
        query = 'SELECT p.po_number as "Purchase Order", v.name as "Vendor", p.po_date as "Date", p.total_amount as "Bill Amount (Rs)", COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = p.po_number), 0) as "Paid Amount (Rs)" FROM po_master p JOIN vendors v ON p.vendor_id = v.id ORDER BY p.po_id DESC'
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df['Balance (Rs)'] = (df['Bill Amount (Rs)'] - df['Paid Amount (Rs)']).astype(float).round(2)
            df['Status'] = df['Balance (Rs)'].apply(lambda x: '✅ Paid' if x <= 0.01 else '⏳ Pending')
            
            today = pd.Timestamp(datetime.date.today())
            df['Days Outstanding'] = (today - pd.to_datetime(df['Date'])).dt.days
            
            utr_df = pd.read_sql_query("SELECT order_no, string_agg(utr_number, ', ') as UTRs FROM payments GROUP BY order_no", conn)
            df = df.merge(utr_df, left_on='Purchase Order', right_on='order_no', how='left').drop(columns=['order_no'])
            df['UTRs'] = df['utrs'].fillna('-')
            df.drop(columns=['utrs'], inplace=True, errors='ignore')
            
            styled_df = df.style.apply(style_aging_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Aging Report as CSV", data=csv, file_name="Vendor_Payables.csv", mime="text/csv", type="primary")
            
            st.divider()
            st.subheader("✏️ Manage Payments & Orders")
            st.write("Edit or delete existing payments below. To edit the actual Bill Amount, go to **Purchase -> PO Records & GRN**.")
            
            selected_po = st.selectbox("Select Purchase Order to Manage Payments", df['Purchase Order'].tolist())
            if selected_po:
                pay_query = "SELECT id, txn_date, payment_mode, amount FROM payments WHERE order_no = %s"
                pay_df = pd.read_sql_query(pay_query, conn, params=[selected_po])
                
                if pay_df.empty:
                    st.info(f"No payments found for {selected_po}.")
                else:
                    for idx, row in pay_df.iterrows():
                        pay_id = row['id']
                        with st.form(key=f"pay_pay_{pay_id}"):
                            st.write(f"**Payment Date:** {row['txn_date']} | **Mode:** {row['payment_mode']}")
                            c1, c2, c3 = st.columns([2, 1, 1])
                            new_amt = c1.number_input("Paid Amount (Rs)", value=float(row['amount']), step=100.0, key=f"amt_{pay_id}")
                            
                            save_btn = c2.form_submit_button("💾 Update")
                            del_btn = c3.form_submit_button("🗑️ Delete")
                            
                            if save_btn:
                                c = conn.cursor()
                                c.execute("UPDATE payments SET amount = %s WHERE id = %s", (new_amt, pay_id))
                                conn.commit()
                                st.success("Payment Updated!")
                                time.sleep(1)
                                st.rerun()
                                
                            if del_btn:
                                c = conn.cursor()
                                c.execute("DELETE FROM payments WHERE id = %s", (pay_id,))
                                conn.commit()
                                st.warning("Payment Deleted!")
                                time.sleep(1)
                                st.rerun()
                                
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("⚠️ Danger Zone: Delete Entire Order"):
                    st.warning(f"This will permanently delete {selected_po}, including all its items, inventory ledgers, and payments.")
                    if st.button("🗑️ Confirm Delete Order", key=f"del_po_{selected_po}"):
                        c = conn.cursor()
                        c.execute("SELECT po_id FROM po_master WHERE po_number = %s", (selected_po,))
                        res = c.fetchone()
                        if res:
                            po_id_del = res[0]
                            c.execute("DELETE FROM po_items WHERE po_id = %s", (po_id_del,))
                            c.execute("DELETE FROM inventory_ledger WHERE ref_type = 'Purchase' AND ref_id = %s", (selected_po,))
                            c.execute("DELETE FROM order_expenses WHERE order_ref = %s", (selected_po,))
                            c.execute("DELETE FROM logistics WHERE order_ref = %s", (selected_po,))
                            c.execute("DELETE FROM payments WHERE order_no = %s", (selected_po,))
                            c.execute("DELETE FROM po_master WHERE po_id = %s", (po_id_del,))
                            conn.commit()
                            st.success(f"{selected_po} completely deleted!")
                            time.sleep(1.5)
                            st.rerun()
        else: st.info("No Purchase Orders found.")
        conn.close()

    elif sub_menu == "Payment Records":
        st.header("Payment History")
        conn = get_db_connection()
        payments_df = pd.read_sql_query('SELECT id, txn_date as "Date", party_type as "Type", order_no as "Order Ref", amount as "Amount (Rs)", payment_mode as "Mode", utr_number as "UTR" FROM payments ORDER BY id DESC', conn)
        show_data_with_delete("payments", payments_df, "PAY-")
        conn.close()

# ==========================================
# 6. LOGISTICS, EXPENSES & OPS
# ==========================================
elif main_menu == "Logistics & Ops":
    if sub_menu == "Add PO/SO Expenses":
        st.header("💸 Add Order-Level Expenses")
        st.write("Add logistics, labour, and packaging costs directly to a specific Purchase Order or Sales Order.")
        
        conn = get_db_connection()
        channel = st.radio("Select Order Type", ["Purchase Orders (PO)", "Sales Orders (SO)"])
        
        if "Purchase" in channel:
            orders_query = "SELECT p.po_number as order_no, p.po_date as o_date, v.name as party_name FROM po_master p JOIN vendors v ON p.vendor_id = v.id ORDER BY p.po_id DESC"
        else:
            orders_query = "SELECT s.so_number as order_no, s.so_date as o_date, c.name as party_name FROM so_master s JOIN clients c ON s.client_id = c.id ORDER BY s.so_id DESC"
            
        orders_df = pd.read_sql_query(orders_query, conn)
        
        if orders_df.empty: st.warning("No orders found. Create an order first.")
        else:
            with st.form("expense_form"):
                col1, col2 = st.columns(2)
                order_dict = {row['order_no']: f"{row['order_no']} | {row['party_name']} | {row['o_date']}" for _, row in orders_df.iterrows()}
                order_ref = col1.selectbox("Select Order Number", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
                notes = col2.text_input("Notes / Details")
                
                st.markdown("### Expense Breakdown")
                c1, c2, c3 = st.columns(3)
                freight = c1.number_input("Logistics/Freight Cost (Rs)", min_value=0.0, step=50.0)
                labour = c2.number_input("Labour Charges (Rs)", min_value=0.0, step=50.0)
                other = c3.number_input("Other Expenses (Rs)", min_value=0.0, step=50.0)
                
                if st.form_submit_button("💾 Save All Expenses to Order"):
                    c = conn.cursor()
                    added = False
                    if freight > 0:
                        c.execute("INSERT INTO order_expenses (order_ref, expense_type, amount, notes, logged_date) VALUES (%s, 'Freight', %s, %s, %s)", (str(order_ref), float(freight), str(notes), str(datetime.date.today())))
                        added = True
                    if labour > 0:
                        c.execute("INSERT INTO order_expenses (order_ref, expense_type, amount, notes, logged_date) VALUES (%s, 'Labour', %s, %s, %s)", (str(order_ref), float(labour), str(notes), str(datetime.date.today())))
                        added = True
                    if other > 0:
                        c.execute("INSERT INTO order_expenses (order_ref, expense_type, amount, notes, logged_date) VALUES (%s, 'Other', %s, %s, %s)", (str(order_ref), float(other), str(notes), str(datetime.date.today())))
                        added = True
                        
                    if added:
                        conn.commit()
                        st.success("✅ Expenses successfully attached to Order!")
                        time.sleep(1.5)
                        st.rerun()
                    else: 
                        st.error("Please enter an amount greater than 0.")
        conn.close()
        
    elif sub_menu == "Add Dispatch Details":
        st.header("🚚 Add Dispatch Details")
        channel = st.radio("Select Channel", ["Purchase (Inbound Pick up)", "Sales (Outbound Dispatch)"])
        conn = get_db_connection()
        if "Purchase" in channel: 
            orders_query = "SELECT p.po_number as order_no, p.po_date as o_date, v.name as party_name FROM po_master p JOIN vendors v ON p.vendor_id = v.id ORDER BY p.po_id DESC"
        else: 
            orders_query = "SELECT s.so_number as order_no, s.so_date as o_date, c.name as party_name FROM so_master s JOIN clients c ON s.client_id = c.id ORDER BY s.so_id DESC"
        
        orders_df = pd.read_sql_query(orders_query, conn)
        
        if orders_df.empty: st.warning(f"No orders found for {channel}. Create an order first.")
        else:
            with st.form("logistics_form"):
                col1, col2 = st.columns(2)
                order_dict = {row['order_no']: f"{row['order_no']} | {row['party_name']} | {row['o_date']}" for _, row in orders_df.iterrows()}
                order_ref = col1.selectbox("Select Order Reference", options=list(order_dict.keys()), format_func=lambda x: order_dict[x])
                
                driver_name = col2.text_input("Driver Name")
                vehicle_no = col1.text_input("Vehicle Number (e.g., KA-01-AB-1234) *")
                from_loc = col2.text_input("From Location *")
                to_loc = col1.text_input("To (Destination) *")
                dist = col2.number_input("Distance (KM)", min_value=0.0, step=1.0)
                freight = col1.number_input("Total Freight Cost (Rs)", min_value=0.0, step=100.0, help="For records only. Add exact monetary deductions in 'Add PO/SO Expenses'.")
                if st.form_submit_button("💾 Save Logistics Details"):
                    if vehicle_no and from_loc and to_loc:
                        c = conn.cursor()
                        c.execute("INSERT INTO logistics (order_ref, from_loc, to_loc, vehicle_no, driver_name, distance_km, freight_cost) VALUES (%s, %s, %s, %s, %s, %s, %s)", (str(order_ref), str(from_loc), str(to_loc), str(vehicle_no), str(driver_name), float(dist), float(freight)))
                        conn.commit()
                        st.success(f"✅ Logistics details saved for {order_ref}!")
                        time.sleep(1.5)
                        st.rerun()
                    else: st.error("Vehicle No, From, and To locations are mandatory.")
        conn.close()
        
    elif sub_menu == "Route & Freight Report":
        st.header("🗺️ Route & Freight Cost Analysis")
        conn = get_db_connection()
        query = 'SELECT l.order_ref as "Order Ref", l.from_loc || \' ➡️ \' || l.to_loc as "Route", l.vehicle_no as "Vehicle", l.driver_name as "Driver", l.distance_km as "Distance (KM)", l.freight_cost as "Freight (Rs)" FROM logistics l ORDER BY l.id DESC'
        log_df = pd.read_sql_query(query, conn)
        if not log_df.empty:
            po_qtys = pd.read_sql_query("SELECT p.po_number as order_no, SUM(i.qty) as total_qty FROM po_master p JOIN po_items i ON p.po_id = i.po_id GROUP BY p.po_id", conn)
            so_qtys = pd.read_sql_query("SELECT s.so_number as order_no, SUM(i.qty) as total_qty FROM so_master s JOIN so_items i ON s.so_id = i.so_id GROUP BY s.so_id", conn)
            all_qtys = pd.concat([po_qtys, so_qtys]).set_index('order_no')
            def get_cost_per_kg(row):
                order = row['Order Ref']
                freight = row['Freight (Rs)']
                if order in all_qtys.index and freight > 0:
                    qty = all_qtys.loc[order, 'total_qty']
                    if qty > 0: return round(freight / qty, 2)
                return 0.0
            log_df['Cost per Kg/Crate (Rs)'] = log_df.apply(get_cost_per_kg, axis=1)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            st.subheader("Total Freight Spent by Route")
            route_summary = log_df.groupby('Route')['Freight (Rs)'].sum().reset_index()
            st.bar_chart(route_summary.set_index('Route'))
        else: st.info("No logistics records found.")
        conn.close()

# ==========================================
# 7. DASHBOARD & SYSTEM ADMIN
# ==========================================
elif main_menu == "Dashboard":
    st.header("📊 Executive Command Center")
    conn = get_db_connection()
    
    # --- 1. THE NUMBER ONE INVESTOR TABLE ---
    st.markdown("### 👔 Investor & Board Summary (Monthly Run-Rate)")
    
    total_rev = pd.read_sql_query("SELECT COALESCE(SUM(total_amount), 0) FROM so_master", conn).iloc[0,0]
    total_cogs = pd.read_sql_query("SELECT COALESCE(SUM(total_amount), 0) FROM po_master", conn).iloc[0,0]
    
    total_freight = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM order_expenses WHERE expense_type='Freight'", conn).iloc[0,0]
    total_labour = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM order_expenses WHERE expense_type='Labour'", conn).iloc[0,0]
    total_other = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM order_expenses WHERE expense_type NOT IN ('Freight', 'Labour')", conn).iloc[0,0]
    
    monthly_payroll = pd.read_sql_query("SELECT COALESCE(SUM(salary_per_day), 0) * 30 FROM employees WHERE status='Active'", conn).iloc[0,0]
    
    total_opex = float(total_freight) + float(total_labour) + float(total_other) + float(monthly_payroll)
    net_profit = float(total_rev) - float(total_cogs) - total_opex
    net_margin = (net_profit / float(total_rev) * 100) if float(total_rev) > 0 else 0.0
    
    investor_df = pd.DataFrame([{
        "Metric": "📈 Gross Revenue", "Value": f"₹ {float(total_rev):,.2f}"
    }, {
        "Metric": "🛒 Cost of Goods Sold (Purchases)", "Value": f"₹ {float(total_cogs):,.2f}"
    }, {
        "Metric": "🚛 Logistics & Freight Costs", "Value": f"₹ {float(total_freight):,.2f}"
    }, {
        "Metric": "🧑‍🌾 Labour Charges (Loading/Unloading)", "Value": f"₹ {float(total_labour):,.2f}"
    }, {
        "Metric": "🏢 Monthly Fixed Payroll (Active Employees x 30)", "Value": f"₹ {float(monthly_payroll):,.2f}"
    }, {
        "Metric": "💎 TRUE NET PROFIT", "Value": f"₹ {net_profit:,.2f}"
    }])
    st.dataframe(investor_df, use_container_width=True, hide_index=True)
    st.caption(f"**True Net Margin (After Logistics, Labour & Payroll): {net_margin:.1f}%**")
    st.divider()

    # --- 2. ALERTS PANEL ---
    st.subheader("🚨 System Alerts")
    stock_df = pd.read_sql_query('SELECT p.id as product_id, p.name, COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) as current_stock, p.default_price FROM products p LEFT JOIN inventory_ledger i ON p.id = i.product_id GROUP BY p.id, p.name, p.default_price', conn)
    low_stock = stock_df[stock_df['current_stock'] < 50]
    if not low_stock.empty: st.warning(f"**Low Stock Alert:** {', '.join(low_stock['name'].tolist())} inventory is running below optimal levels.")
    else: st.success("✅ All inventory levels are optimal. No active incidents.")

    # --- 3. KPI CARDS ---
    st.subheader("🎯 Operational Indicators")
    total_received = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_type='Client'", conn).iloc[0,0]
    total_paid = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_type='Vendor'", conn).iloc[0,0]
    pending_receivables = float(total_rev) - float(total_received)
    pending_payables = float(total_cogs) - float(total_paid)
    
    total_sku_count = stock_df[stock_df['current_stock'] > 0]['current_stock'].sum()
    stock_df['total_value'] = stock_df['current_stock'] * stock_df['default_price']
    total_inventory_value = stock_df['total_value'].sum()
    
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("Total Inventory Value", f"₹{total_inventory_value:,.2f}")
    r2c2.metric("Pending Receivables (From Clients)", f"₹{pending_receivables:,.2f}")
    r2c3.metric("Pending Payables (To Vendors)", f"₹{pending_payables:,.2f}")
    r2c4.metric("Pending SKU (Inventory)", f"{total_sku_count:,.0f} Units")

    # --- 4. CHARTS (DONUT & BAR) ---
    st.divider()
    c1, c2 = st.columns(2)
    sales_by_client = pd.read_sql_query('SELECT c.name as "Client", SUM(s.total_amount) as "Total" FROM so_master s JOIN clients c ON s.client_id = c.id GROUP BY c.name', conn)
    if not sales_by_client.empty:
        fig_donut = px.pie(sales_by_client, values='Total', names='Client', hole=0.4, title="Revenue Share by Client (Donut Chart)")
        c1.plotly_chart(fig_donut, use_container_width=True)
        
    top_products = pd.read_sql_query('SELECT p.name as "Product", SUM(i.qty) as "Volume" FROM so_items i JOIN products p ON i.product_id = p.id GROUP BY p.name ORDER BY "Volume" DESC LIMIT 5', conn)
    if not top_products.empty:
        fig_bar = px.bar(top_products, x='Product', y='Volume', title="Top Products by Volume (Bar Chart)", color='Product')
        c2.plotly_chart(fig_bar, use_container_width=True)
    
    conn.close()

elif main_menu == "System Info":
    st.header("⚙️ User Management & Cloud Status")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("☁️ Database Connection")
        st.success("✅ Connected securely to Neon Cloud Database (PostgreSQL).")
        st.info("💡 Automatic Cloud Backups are active. No manual files needed!")
        
    with col2:
        st.subheader("👥 Add Team Members")
        st.write("Create logins for your field team so they can access the cloud app.")
        with st.form("new_user_form"):
            new_email = st.text_input("New User Email")
            new_pass = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["Sales", "Purchase", "Admin"])
            
            if st.form_submit_button("Create User"):
                conn = get_db_connection()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", (str(new_email), str(new_pass), str(new_role)))
                    conn.commit()
                    st.success(f"User {new_email} created successfully!")
                except psycopg2.IntegrityError:
                    conn.rollback() 
                    st.error("This email already exists!")
                conn.close()