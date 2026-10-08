import streamlit as st
import pandas as pd
import psycopg2
import time
import datetime
import platform
import warnings
import streamlit.components.v1 as components
import plotly.express as px
from database import init_db

warnings.filterwarnings('ignore')

init_db()

def get_db_connection(): return psycopg2.connect(st.secrets["DATABASE_URL"])

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
# MAIN ERP APP 
# ==========================================
st.sidebar.title(f"Welcome, {st.session_state.user_role}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("Main Navigation")

menu_options = []
if st.session_state.user_role == "Admin":
    menu_options = ["Dashboard", "Master Data", "Purchase", "Sales", "Inventory", "Finance", "Logistics", "System Info"]
elif st.session_state.user_role == "Sales":
    menu_options = ["Sales", "Logistics"]
elif st.session_state.user_role == "Purchase":
    menu_options = ["Purchase", "Logistics"]

main_menu = st.sidebar.selectbox("Select Module", menu_options)

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
    sub_menu = st.sidebar.radio("Master Data Options", ["Vendor Onboarding", "Client Onboarding", "Product Master"])
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
            if st.form_submit_button("Save Vendor"):
                if v_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO vendors (name, contact, address, gstin, pan, payment_terms) VALUES (%s, %s, %s, %s, %s, %s)", (str(v_name), str(v_contact), str(v_address), str(v_gstin), str(v_pan), str(v_terms)))
                    conn.commit()
                    conn.close()
                    st.success("Vendor saved!")
                    st.rerun()
        st.subheader("Registered Vendors")
        conn = get_db_connection()
        show_data_with_delete("vendors", pd.read_sql_query("SELECT id, name, contact, gstin FROM vendors", conn), "V")
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
# 2. PURCHASE MODULE
# ==========================================
elif main_menu == "Purchase":
    sub_menu = st.sidebar.radio("Purchase Options", ["Create PO", "PO Records & GRN"])
    if sub_menu == "Create PO":
        st.header("Punch Purchase Order")
        if 'po_cart' not in st.session_state: st.session_state.po_cart = []
        conn = get_db_connection()
        vendors = pd.read_sql_query("SELECT id, name FROM vendors", conn)
        products = pd.read_sql_query("SELECT id, name, tax_rate FROM products", conn)
        conn.close()
        if vendors.empty or products.empty: st.warning("⚠️ Please add Master Data first.")
        else:
            col1, col2 = st.columns(2)
            vendor_dict = {row['id']: f"V{int(row['id']):03d} - {row['name']}" for _, row in vendors.iterrows()}
            selected_vendor_id = col1.selectbox("Select Vendor", options=list(vendor_dict.keys()), format_func=lambda x: vendor_dict[x])
            po_date = col2.date_input("PO Date")
            st.divider()
            with st.form("add_item_form"):
                c1, c2, c3 = st.columns(3)
                prod_dict = {row['id']: f"SKU{int(row['id']):03d} - {row['name']} ({row['tax_rate']}% GST)" for _, row in products.iterrows()}
                selected_prod_id = c1.selectbox("Select Product", options=list(prod_dict.keys()), format_func=lambda x: prod_dict[x])
                qty = c2.number_input("Indent Quantity (Ordered)", min_value=1.0, value=1.0, step=1.0)
                rate = c3.number_input("Rate per unit (Rs)", min_value=0.0, step=10.0)
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
                    st.success(f"Generated {po_number}!")
                    time.sleep(1)
                    st.rerun()

    elif sub_menu == "PO Records & GRN":
        st.header("Update Purchase Orders (GRN)")
        conn = get_db_connection()
        pos = pd.read_sql_query("SELECT po_id, po_number FROM po_master ORDER BY po_id DESC", conn)
        if not pos.empty:
            selected_po = st.selectbox("Select Purchase Order to Update", pos['po_number'].tolist())
            po_id = pos.loc[pos['po_number'] == selected_po, 'po_id'].values[0]
            st.write("✏️ **Double-click the numbers in 'Received_Qty' and 'GRN_Qty' below to edit them!**")
            
            items_query = f'SELECT item_id, p.name as "Product", qty as "Indent_Qty", received_qty as "Received_Qty", grn_qty as "GRN_Qty" FROM po_items i JOIN products p ON i.product_id = p.id WHERE po_id = {po_id}'
            items_df = pd.read_sql_query(items_query, conn)
            
            edited_po_df = st.data_editor(items_df, disabled=["item_id", "Product", "Indent_Qty"], hide_index=True, use_container_width=True)
            if st.button("💾 Save Updates to PO"):
                c = conn.cursor()
                for index, row in edited_po_df.iterrows():
                    c.execute("UPDATE po_items SET received_qty = %s, grn_qty = %s WHERE item_id = %s", (float(row['Received_Qty']), float(row['GRN_Qty']), int(row['item_id'])))
                conn.commit()
                st.success(f"Tracking quantities saved for {selected_po}!")
                
            # --- PURCHASE (GRN BASED) INVOICE ---
            st.divider()
            st.subheader("🧾 Generate GRN Settlement Invoice")
            if st.button("🖨️ Preview & Print PO Invoice"):
                c = conn.cursor()
                c.execute("SELECT v.name, v.contact, v.gstin, p.po_date FROM po_master p JOIN vendors v ON p.vendor_id = v.id WHERE p.po_id = %s", (int(po_id),))
                vendor_info = c.fetchone()
                
                c.execute(f"SELECT pr.name, i.rate, i.grn_qty FROM po_items i JOIN products pr ON i.product_id = pr.id WHERE i.po_id = {po_id}")
                invoice_items = c.fetchall()
                
                items_html = ""
                calculated_total = 0.0
                for idx, item in enumerate(invoice_items):
                    actual_qty = float(item[2]) if item[2] is not None else 0.0
                    item_total = float(item[1]) * actual_qty
                    calculated_total += item_total
                    items_html += f"<tr><td style='padding:10px; border:1px solid #ddd; text-align:left;'>{idx+1}</td><td style='padding:10px; border:1px solid #ddd; text-align:left;'>{item[0]}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{float(item[1]):.2f}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{actual_qty}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{item_total:.2f}</td></tr>"
                
                invoice_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 40px; border: 1px solid #ddd; background-color: #fff; color: #000;">
                    <h1 style="text-align: center; color: #444; margin-bottom: 5px; font-weight: normal; letter-spacing: 2px;">PURCHASE / GRN INVOICE</h1>
                    <p style="text-align: center; color: #2e7d32; margin-top: 0; font-size: 18px;"><b>KAMADHENU FARM FRESH PRIVATE LIMITED</b></p>
                    
                    <div style="display: flex; justify-content: space-between; margin-top: 30px; font-size: 14px;">
                        <div style="width: 50%;">
                            <p style="margin: 0; line-height: 1.5;">
                                Building No./Flat No.: 1697<br>
                                Road/Street: 19th Main Road<br>
                                Locality/Sub Locality: HSR Layout<br>
                                Bengaluru, Karnataka, 560102<br>
                                Mobile: +91 9206692624<br>
                                Email: kamadhenufreshfarms@gmail.com
                            </p>
                        </div>
                        <div style="width: 40%; text-align: left;">
                            <p style="margin: 0; line-height: 1.5;">
                                <b>Order #:</b> {selected_po}<br>
                                <b>Order Date:</b> {vendor_info[3]}
                            </p>
                            <div style="margin-top: 15px;">
                                <b>Vendor Details:</b><br>
                                {vendor_info[0]}<br>
                                Ph: {vendor_info[1]}<br>
                                GSTIN: {vendor_info[2]}
                            </div>
                        </div>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 30px; font-size: 14px;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">#</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Item</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Rate / Item</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">GRN Qty</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Amount (₹)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>
                    
                    <h3 style="text-align: right; margin-top: 15px; color: #333;">Total Payable: ₹{calculated_total:,.2f}</h3>
                    
                    <div style="display: flex; justify-content: space-between; margin-top: 40px; font-size: 14px;">
                        <div style="line-height: 1.6;">
                            <b style="color: #444;">Bank Details:</b><br>
                            <b>Bank:</b> FEDERAL BANK<br>
                            <b>Account Holder:</b> KAMADHENU FARM FRESH PRIVATE LIMITED<br>
                            <b>Account #:</b> 25730200001058<br>
                            <b>IFSC Code:</b> FDRL0002573
                        </div>
                        <div style="text-align: center;">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=upi://pay?pa=25730200001058@FDRL0002573.ifsc.npci&pn=Kamadhenu&am={calculated_total}" alt="QR Code">
                            <div style="font-size: 11px; margin-top: 5px;">Scan to Pay via UPI</div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 40px;" class="no-print">
                        <button onclick="window.print()" style="padding: 10px 20px; background-color: #2e7d32; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; font-size: 16px;">🖨️ Print or Save as PDF</button>
                        <style>
                            @media print {{
                                .no-print {{ display: none !important; }}
                                body {{ -webkit-print-color-adjust: exact; }}
                            }}
                        </style>
                    </div>
                </div>
                """
                components.html(invoice_html, height=850, scrolling=True)
                
        conn.close()

# ==========================================
# 3. SALES MODULE
# ==========================================
elif main_menu == "Sales":
    sub_menu = st.sidebar.radio("Sales Options", ["Create Sales Order", "Sales Records & Tracking"])
    if sub_menu == "Create Sales Order":
        st.header("Punch Sales Order")
        if 'so_cart' not in st.session_state: st.session_state.so_cart = []
        conn = get_db_connection()
        clients = pd.read_sql_query("SELECT id, name FROM clients", conn)
        products = pd.read_sql_query("SELECT id, name, tax_rate, default_price FROM products", conn)
        conn.close()
        
        if not clients.empty and not products.empty:
            col1, col2, col3 = st.columns(3)
            client_dict = {row['id']: f"S-{int(row['id']):03d} - {row['name']}" for _, row in clients.iterrows()}
            selected_client_id = col1.selectbox("Select Client", options=list(client_dict.keys()), format_func=lambda x: client_dict[x])
            so_date = col2.date_input("Sales Date")
            delivery_date = col3.date_input("Delivery Date")
            st.divider()
            with st.form("add_so_item_form"):
                c1, c2, c3 = st.columns(3)
                prod_dict = {row['id']: f"SKU{int(row['id']):03d} - {row['name']} ({row['tax_rate']}% GST)" for _, row in products.iterrows()}
                selected_prod_id = c1.selectbox("Select Product", options=list(prod_dict.keys()), format_func=lambda x: prod_dict[x])
                suggested_price = float(products.loc[products['id'] == selected_prod_id, 'default_price'].values[0])
                qty = c2.number_input("Order Quantity", min_value=1.0, value=1.0, step=1.0)
                rate = c3.number_input("Rate per unit (Rs)", min_value=0.0, value=float(suggested_price), step=10.0)
                if st.form_submit_button("➕ Click to Add Item"):
                    tax_rate = float(products.loc[products['id'] == selected_prod_id, 'tax_rate'].values[0])
                    base_total = float(qty * rate)
                    gst_amount = float(base_total * (tax_rate / 100))
                    
                    st.session_state.so_cart.append({
                        "prod_id": int(selected_prod_id), 
                        "Product": str(prod_dict[selected_prod_id]), 
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
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM so_master")
                    so_number = f"SO-{(c.fetchone()[0] + 1):04d}"
                    grand_total = float(cart_df['Total Rs'].sum())
                    
                    c.execute("INSERT INTO so_master (so_number, client_id, so_date, delivery_date, total_amount, status) VALUES (%s, %s, %s, %s, %s, %s) RETURNING so_id", (str(so_number), int(selected_client_id), str(so_date), str(delivery_date), grand_total, "Pending"))
                    new_so_id = int(c.fetchone()[0])
                    
                    for item in st.session_state.so_cart:
                        c.execute("INSERT INTO so_items (so_id, product_id, qty, rate, gst_amount, total) VALUES (%s, %s, %s, %s, %s, %s)", 
                                  (new_so_id, int(item['prod_id']), float(item['Order Qty']), float(item['Rate']), float(item['GST Rs']), float(item['Total Rs'])))
                        c.execute("INSERT INTO inventory_ledger (product_id, batch_no, qty_in, qty_out, ref_type, ref_id, txn_date) VALUES (%s, 'AUTO', 0, %s, 'Sale', %s, %s)", 
                                  (int(item['prod_id']), float(item['Order Qty']), str(so_number), str(so_date)))
                    conn.commit()
                    conn.close()
                    st.session_state.so_cart = []
                    st.success(f"Generated {so_number}!")
                    time.sleep(1)
                    st.rerun()

    elif sub_menu == "Sales Records & Tracking":
        st.header("Update Sales Orders (Dispatch & Returns)")
        conn = get_db_connection()
        sos = pd.read_sql_query("SELECT so_id, so_number FROM so_master ORDER BY so_id DESC", conn)
        if not sos.empty:
            selected_so = st.selectbox("Select Sales Order to Update", sos['so_number'].tolist())
            so_id = sos.loc[sos['so_number'] == selected_so, 'so_id'].values[0]
            st.write("✏️ **Double-click the numbers below to edit Dispatch Qty, Client Received Qty, and Rejected Qty:**")
            
            items_query = f'SELECT item_id, p.name as "Product", qty as "Order_Qty", dispatch_qty as "Dispatch_Qty", received_qty as "Client_Received_Qty", rejected_qty as "Rejected_Qty" FROM so_items i JOIN products p ON i.product_id = p.id WHERE so_id = {so_id}'
            items_df = pd.read_sql_query(items_query, conn)
            
            edited_so_df = st.data_editor(items_df, disabled=["item_id", "Product", "Order_Qty"], hide_index=True, use_container_width=True)
            if st.button("💾 Save Updates to SO"):
                c = conn.cursor()
                for index, row in edited_so_df.iterrows():
                    c.execute("UPDATE so_items SET dispatch_qty = %s, received_qty = %s, rejected_qty = %s WHERE item_id = %s", (float(row['Dispatch_Qty']), float(row['Client_Received_Qty']), float(row['Rejected_Qty']), int(row['item_id'])))
                conn.commit()
                st.success(f"Tracking quantities saved for {selected_so}!")
                
            # --- SALES (CLIENT RECEIVED BASED) INVOICE ---
            st.divider()
            st.subheader("🧾 Generate Professional Invoice")
            if st.button("🖨️ Preview & Print Invoice"):
                c = conn.cursor()
                c.execute("SELECT c.name, c.contact, c.gstin, s.so_date FROM so_master s JOIN clients c ON s.client_id = c.id WHERE s.so_id = %s", (int(so_id),))
                client_info = c.fetchone()
                
                c.execute(f"SELECT p.name, i.rate, i.received_qty FROM so_items i JOIN products p ON i.product_id = p.id WHERE i.so_id = {so_id}")
                invoice_items = c.fetchall()
                
                items_html = ""
                calculated_total = 0.0
                for idx, item in enumerate(invoice_items):
                    actual_qty = float(item[2]) if item[2] is not None else 0.0
                    item_total = float(item[1]) * actual_qty
                    calculated_total += item_total
                    items_html += f"<tr><td style='padding:10px; border:1px solid #ddd; text-align:left;'>{idx+1}</td><td style='padding:10px; border:1px solid #ddd; text-align:left;'>{item[0]}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{float(item[1]):.2f}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{actual_qty}</td><td style='padding:10px; border:1px solid #ddd; text-align:right;'>{item_total:.2f}</td></tr>"
                
                invoice_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 40px; border: 1px solid #ddd; background-color: #fff; color: #000;">
                    <h1 style="text-align: center; color: #444; margin-bottom: 5px; font-weight: normal; letter-spacing: 2px;">INVOICE</h1>
                    <p style="text-align: center; color: #2e7d32; margin-top: 0; font-size: 18px;"><b>KAMADHENU FARM FRESH PRIVATE LIMITED</b></p>
                    
                    <div style="display: flex; justify-content: space-between; margin-top: 30px; font-size: 14px;">
                        <div style="width: 50%;">
                            <p style="margin: 0; line-height: 1.5;">
                                Building No./Flat No.: 1697<br>
                                Road/Street: 19th Main Road<br>
                                Locality/Sub Locality: HSR Layout<br>
                                Bengaluru, Karnataka, 560102<br>
                                Mobile: +91 9206692624<br>
                                Email: kamadhenufreshfarms@gmail.com
                            </p>
                        </div>
                        <div style="width: 40%; text-align: left;">
                            <p style="margin: 0; line-height: 1.5;">
                                <b>Invoice #:</b> {selected_so}<br>
                                <b>Invoice Date:</b> {client_info[3]}
                            </p>
                            <div style="margin-top: 15px;">
                                <b>Customer Details:</b><br>
                                {client_info[0]}<br>
                                Ph: {client_info[1]}<br>
                                GSTIN: {client_info[2]}
                            </div>
                        </div>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 30px; font-size: 14px;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">#</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Item</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Rate / Item</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Received Qty</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Amount (₹)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>
                    
                    <h3 style="text-align: right; margin-top: 15px; color: #333;">Total Payable: ₹{calculated_total:,.2f}</h3>
                    
                    <div style="display: flex; justify-content: space-between; margin-top: 40px; font-size: 14px;">
                        <div style="line-height: 1.6;">
                            <b style="color: #444;">Bank Details:</b><br>
                            <b>Bank:</b> FEDERAL BANK<br>
                            <b>Account Holder:</b> KAMADHENU FARM FRESH PRIVATE LIMITED<br>
                            <b>Account #:</b> 25730200001058<br>
                            <b>IFSC Code:</b> FDRL0002573
                        </div>
                        <div style="text-align: center;">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=upi://pay?pa=25730200001058@FDRL0002573.ifsc.npci&pn=Kamadhenu&am={calculated_total}" alt="QR Code">
                            <div style="font-size: 11px; margin-top: 5px;">Scan to Pay via UPI</div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 40px;" class="no-print">
                        <button onclick="window.print()" style="padding: 10px 20px; background-color: #2e7d32; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; font-size: 16px;">🖨️ Print or Save as PDF</button>
                        <style>
                            @media print {{
                                .no-print {{ display: none !important; }}
                                body {{ -webkit-print-color-adjust: exact; }}
                            }}
                        </style>
                    </div>
                </div>
                """
                components.html(invoice_html, height=850, scrolling=True)
        conn.close()

# ==========================================
# 4. INVENTORY MODULE
# ==========================================
elif main_menu == "Inventory":
    sub_menu = st.sidebar.radio("Inventory Options", ["Live Stock", "Ledger History"])
    if sub_menu == "Live Stock":
        st.header("📦 Live Stock Tracker")
        conn = get_db_connection()
        stock_df = pd.read_sql_query('SELECT p.id as "SKU ID", p.name as "Product Name", p.category as "Category", COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) as "Current Stock" FROM products p LEFT JOIN inventory_ledger i ON p.id = i.product_id GROUP BY p.id', conn)
        if not stock_df.empty:
            stock_df['SKU ID'] = stock_df['SKU ID'].apply(lambda x: f"SKU{int(x):03d}")
            st.dataframe(stock_df, use_container_width=True, hide_index=True)
        conn.close()
    elif sub_menu == "Ledger History":
        st.header("Inventory Ledger")
        conn = get_db_connection()
        ledger_df = pd.read_sql_query('SELECT i.txn_date as "Date", p.name as "Product", i.ref_type as "Type", i.ref_id as "Reference", i.qty_in as "Qty IN", i.qty_out as "Qty OUT" FROM inventory_ledger i JOIN products p ON i.product_id = p.id ORDER BY i.ledger_id DESC', conn)
        if not ledger_df.empty: st.dataframe(ledger_df, use_container_width=True, hide_index=True)
        conn.close()

# ==========================================
# 5. FINANCE MODULE 
# ==========================================
elif main_menu == "Finance":
    sub_menu = st.sidebar.radio("Finance Options", ["Add Payment", "Receivables (Client Bills)", "Payables (Vendor Bills)", "Payment Records (Edit/Delete)"])
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
        st.header("📈 Client Receivables (Bill-wise)")
        conn = get_db_connection()
        query = 'SELECT s.so_number as "Sales Order", c.name as "Client", s.so_date as "Date", s.total_amount as "Bill Amount (Rs)", COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = s.so_number), 0) as "Paid Amount (Rs)" FROM so_master s JOIN clients c ON s.client_id = c.id ORDER BY s.so_id DESC'
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df['Balance (Rs)'] = (df['Bill Amount (Rs)'] - df['Paid Amount (Rs)']).astype(float).round(2)
            df['Status'] = df['Balance (Rs)'].apply(lambda x: '✅ Payment Made' if x <= 0.01 else '⏳ Pending')
            utr_df = pd.read_sql_query("SELECT order_no, string_agg(utr_number, ', ') as UTRs FROM payments GROUP BY order_no", conn)
            df = df.merge(utr_df, left_on='Sales Order', right_on='order_no', how='left').drop(columns=['order_no'])
            df['UTRs'] = df['utrs'].fillna('-')
            df.drop(columns=['utrs'], inplace=True, errors='ignore')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("No Sales Orders found.")
        conn.close()
            
    elif sub_menu == "Payables (Vendor Bills)":
        st.header("📉 Vendor Payables (Bill-wise)")
        conn = get_db_connection()
        query = 'SELECT p.po_number as "Purchase Order", v.name as "Vendor", p.po_date as "Date", p.total_amount as "Bill Amount (Rs)", COALESCE((SELECT SUM(amount) FROM payments WHERE order_no = p.po_number), 0) as "Paid Amount (Rs)" FROM po_master p JOIN vendors v ON p.vendor_id = v.id ORDER BY p.po_id DESC'
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df['Balance (Rs)'] = (df['Bill Amount (Rs)'] - df['Paid Amount (Rs)']).astype(float).round(2)
            df['Status'] = df['Balance (Rs)'].apply(lambda x: '✅ Payment Made' if x <= 0.01 else '⏳ Pending')
            utr_df = pd.read_sql_query("SELECT order_no, string_agg(utr_number, ', ') as UTRs FROM payments GROUP BY order_no", conn)
            df = df.merge(utr_df, left_on='Purchase Order', right_on='order_no', how='left').drop(columns=['order_no'])
            df['UTRs'] = df['utrs'].fillna('-')
            df.drop(columns=['utrs'], inplace=True, errors='ignore')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("No Purchase Orders found.")
        conn.close()

    elif sub_menu == "Payment Records (Edit/Delete)":
        st.header("Payment History")
        conn = get_db_connection()
        payments_df = pd.read_sql_query('SELECT id, txn_date as "Date", party_type as "Type", order_no as "Order Ref", amount as "Amount (Rs)", payment_mode as "Mode", utr_number as "UTR" FROM payments ORDER BY id DESC', conn)
        show_data_with_delete("payments", payments_df, "PAY-")
        conn.close()

# ==========================================
# 6. LOGISTICS MODULE
# ==========================================
elif main_menu == "Logistics":
    sub_menu = st.sidebar.radio("Logistics Options", ["Add Dispatch Details", "Route & Freight Report"])
    if sub_menu == "Add Dispatch Details":
        st.header("🚚 Add Dispatch & Freight Details")
        channel = st.radio("Select Channel", ["Purchase (Inbound Pick up)", "Sales (Outbound Dispatch)"])
        conn = get_db_connection()
        if "Purchase" in channel: orders_df = pd.read_sql_query("SELECT po_number as order_no FROM po_master", conn)
        else: orders_df = pd.read_sql_query("SELECT so_number as order_no FROM so_master", conn)
        all_orders = orders_df['order_no'].tolist()
        
        if not all_orders: st.warning(f"No orders found for {channel}. Create an order first.")
        else:
            with st.form("logistics_form"):
                col1, col2 = st.columns(2)
                order_ref = col1.selectbox("Select Order Reference", all_orders)
                driver_name = col2.text_input("Driver Name")
                vehicle_no = col1.text_input("Vehicle Number (e.g., KA-01-AB-1234) *")
                from_loc = col2.text_input("From Location *")
                to_loc = col1.text_input("To (Destination) *")
                dist = col2.number_input("Distance (KM)", min_value=0.0, step=1.0)
                freight = col1.number_input("Total Freight Cost (Rs)", min_value=0.0, step=100.0)
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
    st.header("📊 AI-Powered Business Dashboard")
    st.markdown("""
    **Welcome to your Command Center!** 
    This module combines interactive 3D visualizations, analytical charts, and real-time tracking to give you a multidimensional view of your farm's performance.
    """)
    
    conn = get_db_connection()
    
    # --- 1. ALERTS & INCIDENT PANEL ---
    st.subheader("🚨 System Alerts")
    stock_df = pd.read_sql_query('SELECT p.name, COALESCE(SUM(i.qty_in), 0) - COALESCE(SUM(i.qty_out), 0) as current_stock FROM products p LEFT JOIN inventory_ledger i ON p.id = i.product_id GROUP BY p.name', conn)
    low_stock = stock_df[stock_df['current_stock'] < 50]
    if not low_stock.empty:
        st.warning(f"**Low Stock Alert:** {', '.join(low_stock['name'].tolist())} inventory is running below optimal levels.")
    else:
        st.success("✅ All inventory levels are optimal. No active incidents.")

    # --- 2. KPI CARDS ---
    st.subheader("🎯 Key Performance Indicators")
    total_sales = pd.read_sql_query("SELECT COALESCE(SUM(total_amount), 0) FROM so_master", conn).iloc[0,0]
    total_purchases = pd.read_sql_query("SELECT COALESCE(SUM(total_amount), 0) FROM po_master", conn).iloc[0,0]
    total_received = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_type='Client'", conn).iloc[0,0]
    total_paid = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_type='Vendor'", conn).iloc[0,0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"₹{float(total_sales):,.2f}")
    col2.metric("Total Cost", f"₹{float(total_purchases):,.2f}")
    profit = float(total_sales) - float(total_purchases)
    col3.metric("Gross Profit", f"₹{profit:,.2f}", delta=f"Margin: {(profit/float(total_sales)*100 if total_sales > 0 else 0):.1f}%")
    col4.metric("Pending Receivables", f"₹{(float(total_sales) - float(total_received)):,.2f}")

    # --- 3. CHARTS (DONUT & BAR) ---
    c1, c2 = st.columns(2)
    sales_by_client = pd.read_sql_query("SELECT c.name as Client, SUM(s.total_amount) as Total FROM so_master s JOIN clients c ON s.client_id = c.id GROUP BY c.name", conn)
    if not sales_by_client.empty:
        fig_donut = px.pie(sales_by_client, values='Total', names='Client', hole=0.4, title="Revenue Share by Client (Donut Chart)")
        c1.plotly_chart(fig_donut, use_container_width=True)
        
    top_products = pd.read_sql_query("SELECT p.name as Product, SUM(i.qty) as Volume FROM so_items i JOIN products p ON i.product_id = p.id GROUP BY p.name ORDER BY Volume DESC LIMIT 5", conn)
    if not top_products.empty:
        fig_bar = px.bar(top_products, x='Product', y='Volume', title="Top Products by Volume (Bar Chart)", color='Product')
        c2.plotly_chart(fig_bar, use_container_width=True)
        
    # --- 4. LINE CHART (TRENDS) & FUNNEL ---
    c3, c4 = st.columns(2)
    sales_trend = pd.read_sql_query("SELECT so_date as Date, SUM(total_amount) as Revenue FROM so_master GROUP BY so_date ORDER BY so_date", conn)
    if not sales_trend.empty:
        fig_line = px.line(sales_trend, x='Date', y='Revenue', markers=True, title="Revenue Timeline / Trends (Line Chart)")
        c3.plotly_chart(fig_line, use_container_width=True)
        
    funnel_data = pd.DataFrame({
        'Stage': ['Orders Placed', 'Dispatched', 'Payments Received'],
        'Count': [
            pd.read_sql_query("SELECT COUNT(*) FROM so_master", conn).iloc[0,0],
            pd.read_sql_query("SELECT COUNT(*) FROM logistics WHERE order_ref LIKE 'SO%'", conn).iloc[0,0],
            pd.read_sql_query("SELECT COUNT(DISTINCT order_no) FROM payments WHERE party_type='Client'", conn).iloc[0,0]
        ]
    })
    if funnel_data['Count'].sum() > 0:
        fig_funnel = px.funnel(funnel_data, x='Count', y='Stage', title="Sales Process Funnel")
        c4.plotly_chart(fig_funnel, use_container_width=True)

    # --- 5. 3D CUBE VISUALIZATION ---
    st.divider()
    st.subheader("🧊 3D Multidimensional Data Cube")
    st.markdown("Rotate and zoom this interactive 3D model to analyze the relationship between Order Volume, Pricing, and Total Revenue across your products.")
    cube_df = pd.read_sql_query("SELECT p.name as Product, p.category as Category, i.qty as Quantity, i.rate as Rate, i.total as Total FROM so_items i JOIN products p ON i.product_id = p.id", conn)
    if not cube_df.empty and len(cube_df) > 0:
        fig_3d = px.scatter_3d(cube_df, x='Quantity', y='Rate', z='Total', color='Category', hover_name='Product', size_max=18, title="3D Cube: Volume vs Pricing vs Revenue")
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("Punch a few Sales Orders to render the interactive 3D Data Cube!")
        
    # --- 6. TIME SERIES TABLE ---
    st.subheader("📅 Tabular Data Records")
    if not sales_trend.empty:
        st.dataframe(sales_trend, use_container_width=True, hide_index=True)
    
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