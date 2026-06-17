import streamlit as st
import sqlite3
import pandas as pd
from decimal import Decimal
from datetime import datetime, timedelta
import traceback

# ---- MUST BE FIRST ----
st.set_page_config(
    page_title="BankDB Transaction Monitoring System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- DEBUG ----
#st.write("✅ App started successfully")  # This confirms the script runs

# ---- SIMPLE, SAFE STYLING (no heavy CSS) ----
st.markdown("""
    <style>
        /* Subtle dark background */
        .stApp {
            background: #0e1117;
        }
        /* Make metric cards nicer */
        [data-testid="metric-container"] {
            background: #1a1e2b;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #2d3346;
        }
        /* Buttons */
        .stButton button {
            background: #22d3ee;
            color: #000;
            border-radius: 8px;
            font-weight: 600;
        }
        .stButton button:hover {
            background: #06b6d4;
        }
        /* Headers */
        h1, h2, h3 {
            color: #22d3ee;
        }
    </style>
""", unsafe_allow_html=True)

# ---- SESSION STATE ----
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_customer_id" not in st.session_state:
    st.session_state.user_customer_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "success_msg" not in st.session_state:
    st.session_state.success_msg = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = None

st.title("🏦 BankDB Transaction Monitoring System")
st.caption("Secure banking operations • SQLite • Real‑time monitoring")
st.markdown("---")

# ---- DATABASE SETUP ----
DB_FILE = "bankdb.sqlite"

def get_connection():
    """Create and return a database connection, initializing tables/triggers."""
    try:
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        initialize_database(conn)
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}\n{traceback.format_exc()}")
        st.stop()

def initialize_database(conn):
    """Create all tables and triggers if they don't exist."""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # ---- TABLES ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lock_until DATETIME DEFAULT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_number INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            branch TEXT,
            balance NUMERIC(12,2) DEFAULT 1000 CHECK (balance >= 1000),
            account_type TEXT CHECK(account_type IN ('savings','current')),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    # Ensure sequence starts at 1001 (so account numbers are 1001, 1002, ...)
    cur.execute("INSERT OR IGNORE INTO sqlite_sequence (name, seq) VALUES ('accounts', 1000)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number INTEGER,
            transaction_type TEXT CHECK(transaction_type IN ('deposit','withdraw')),
            amount NUMERIC(12,2),
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number INTEGER,
            amount NUMERIC(12,2),
            alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            operation_type TEXT,
            record_id TEXT,
            old_data TEXT,
            new_data TEXT,
            action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            event_type TEXT,
            failed_attempts INTEGER,
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # ---- DROP & RECREATE TRIGGERS (to avoid duplicates) ----
    trigger_names = [
        "high_value_transaction_alert",
        "customer_insert_log",
        "customer_update_log",
        "customer_delete_log",
        "account_insert_log",
        "account_update_log",
        "account_delete_log",
        "customer_failed_login",
        "customer_locked",
        "customer_unlocked"
    ]
    for t in trigger_names:
        cur.execute(f"DROP TRIGGER IF EXISTS {t}")

    # Create triggers (each statement is a complete SQL command)
    cur.execute("""
        CREATE TRIGGER high_value_transaction_alert
        AFTER INSERT ON transactions
        WHEN NEW.amount >= 50000
        BEGIN
            INSERT INTO alerts(account_number, amount, message)
            VALUES (NEW.account_number, NEW.amount, 'High value ' || NEW.transaction_type || ' detected');
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_insert_log
        AFTER INSERT ON customers
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('customers','INSERT',NEW.customer_id,NULL,
                    'Name:'||NEW.full_name||', Email:'||NEW.email||', Phone:'||NEW.phone||', City:'||NEW.city);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_update_log
        AFTER UPDATE ON customers
        WHEN OLD.full_name <> NEW.full_name OR OLD.email <> NEW.email OR OLD.phone <> NEW.phone OR OLD.city <> NEW.city
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('customers','UPDATE',NEW.customer_id,
                    'Name:'||OLD.full_name||', Email:'||OLD.email||', Phone:'||OLD.phone||', City:'||OLD.city,
                    'Name:'||NEW.full_name||', Email:'||NEW.email||', Phone:'||NEW.phone||', City:'||NEW.city);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_delete_log
        AFTER DELETE ON customers
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('customers','DELETE',OLD.customer_id,
                    'Name:'||OLD.full_name||', Email:'||OLD.email||', Phone:'||OLD.phone||', City:'||OLD.city,
                    NULL);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER account_insert_log
        AFTER INSERT ON accounts
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('accounts','INSERT',NEW.account_number,NULL,
                    'Customer ID:'||NEW.customer_id||', Branch:'||NEW.branch||', Type:'||NEW.account_type||', Balance:'||NEW.balance);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER account_update_log
        AFTER UPDATE ON accounts
        WHEN OLD.branch <> NEW.branch OR OLD.account_type <> NEW.account_type
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('accounts','UPDATE',NEW.account_number,
                    'Branch:'||OLD.branch||', Type:'||OLD.account_type,
                    'Branch:'||NEW.branch||', Type:'||NEW.account_type);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER account_delete_log
        AFTER DELETE ON accounts
        BEGIN
            INSERT INTO admin_logs (table_name, operation_type, record_id, old_data, new_data)
            VALUES ('accounts','DELETE',OLD.account_number,
                    'Customer ID:'||OLD.customer_id||', Branch:'||OLD.branch||', Type:'||OLD.account_type||', Balance:'||OLD.balance,
                    NULL);
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_failed_login
        AFTER UPDATE ON customers
        WHEN NEW.failed_attempts > OLD.failed_attempts
        BEGIN
            INSERT INTO security_logs (customer_id, event_type, failed_attempts, details)
            VALUES (NEW.customer_id, 'FAILED_LOGIN', NEW.failed_attempts, 'Invalid login attempt');
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_locked
        AFTER UPDATE ON customers
        WHEN NEW.lock_until IS NOT NULL AND OLD.lock_until IS NULL
        BEGIN
            INSERT INTO security_logs (customer_id, event_type, failed_attempts, details)
            VALUES (NEW.customer_id, 'ACCOUNT_LOCKED', NEW.failed_attempts, 'Account locked due to max attempts');
        END;
    """)

    cur.execute("""
        CREATE TRIGGER customer_unlocked
        AFTER UPDATE ON customers
        WHEN NEW.lock_until IS NULL AND OLD.lock_until IS NOT NULL
        BEGIN
            INSERT INTO security_logs (customer_id, event_type, failed_attempts, details)
            VALUES (NEW.customer_id, 'ACCOUNT_UNLOCKED', 0, 'Account unlocked by admin');
        END;
    """)

    conn.commit()

def perform_transaction(conn, acc_no, txn_type, amount):
    cur = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE account_number = ?", (acc_no,))
    row = cur.fetchone()
    if row is None:
        raise ValueError("Account not found")
    balance = row[0]

    if txn_type == 'deposit':
        new_balance = balance + amount
        cur.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_no))
        cur.execute("INSERT INTO transactions(account_number, transaction_type, amount) VALUES (?,?,?)",
                    (acc_no, 'deposit', amount))
    elif txn_type == 'withdraw':
        if balance - amount < 1000:
            raise ValueError("Minimum balance of 1000 must be maintained")
        new_balance = balance - amount
        cur.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_no))
        cur.execute("INSERT INTO transactions(account_number, transaction_type, amount) VALUES (?,?,?)",
                    (acc_no, 'withdraw', amount))
    else:
        raise ValueError("Invalid transaction type")
    conn.commit()

# ---- LOGIN PAGE ----
if not st.session_state.logged_in:
    st.title("Login")
    login_type = st.radio("Login As", ["Admin", "User"], horizontal=True)

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        if login_type == "Admin":
            if username == "admin" and password == "admin@1234":
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.success("Admin login successful")
                st.rerun()
            else:
                st.error("Invalid admin credentials")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT customer_id, full_name, failed_attempts, lock_until
                    FROM customers
                    WHERE full_name = ? AND email = ?
                """, (username.strip(), password.strip()))
                user = cur.fetchone()

                if user:
                    lock_until = user["lock_until"]
                    if lock_until and datetime.now() < datetime.fromisoformat(lock_until):
                        remaining = int((datetime.fromisoformat(lock_until) - datetime.now()).total_seconds() // 60)
                        st.error(f"Account locked. Try again in {remaining} minutes")
                    else:
                        cur.execute("""
                            UPDATE customers
                            SET failed_attempts = 0, lock_until = NULL
                            WHERE customer_id = ?
                        """, (user["customer_id"],))
                        conn.commit()
                        st.session_state.logged_in = True
                        st.session_state.role = "user"
                        st.session_state.user_customer_id = user["customer_id"]
                        st.session_state.user_name = user["full_name"]
                        st.success("User login successful")
                        conn.close()
                        st.rerun()
                else:
                    # Failed login: increment attempts
                    cur.execute("SELECT customer_id, failed_attempts FROM customers WHERE full_name = ?", (username.strip(),))
                    fail_user = cur.fetchone()
                    if fail_user:
                        new_attempts = fail_user["failed_attempts"] + 1
                        if new_attempts >= 3:
                            lock_time = datetime.now() + timedelta(minutes=5)
                            cur.execute("""
                                UPDATE customers
                                SET failed_attempts = ?, lock_until = ?
                                WHERE customer_id = ?
                            """, (new_attempts, lock_time.isoformat(), fail_user["customer_id"]))
                            st.error("Account locked after 3 failed attempts. Try again after 5 minutes")
                        else:
                            cur.execute("""
                                UPDATE customers
                                SET failed_attempts = ?
                                WHERE customer_id = ?
                            """, (new_attempts, fail_user["customer_id"]))
                            remaining = 3 - new_attempts
                            st.error(f"Invalid credentials. {remaining} attempts remaining")
                        conn.commit()
                    else:
                        st.error("Invalid user credentials")
                    conn.close()
            except Exception as e:
                st.error(f"Login error: {e}")
    st.stop()

# ---- SIDEBAR MENU ----
st.sidebar.markdown("### Navigation")

if st.session_state.role == "admin":
    menu = st.sidebar.selectbox(
        "Select Operation",
        (
            "Home",
            "Add Customer",
            "View Customers",
            "Edit / Delete Customers",
            "Create Account",
            "View Accounts",
            "Edit / Delete Accounts",
            "Deposit / Withdraw",
            "Check Balance",
            "View Transactions",
            "View Alerts",
            "Admin Logs",
            "Locked Accounts",
            "Security Logs"
        )
    )
else:
    menu = st.sidebar.selectbox(
        "Select Operation",
        (
            "Home",
            "Create Account",
            "View Accounts",
            "Deposit / Withdraw",
            "Check Balance",
            "View Transactions"
        )
    )

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---- GLOBAL MESSAGES ----
if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = None
if st.session_state.error_msg:
    st.error(st.session_state.error_msg)
    st.session_state.error_msg = None

# ---- MENU OPERATIONS ----
# HOME
if menu == "Home":
    st.markdown("## BankDB Transaction Monitoring System")
    st.markdown("Welcome to **BankDB**, a secure banking application designed for real‑time transaction monitoring, role‑based access control, and complete administrative auditing.")
    st.markdown("---")
    if st.session_state.role == "admin":
        st.markdown("### Admin Dashboard")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customers")
        total_customers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM accounts")
        total_accounts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alerts")
        total_alerts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM customers WHERE lock_until IS NOT NULL AND lock_until > datetime('now')")
        locked_accounts = cur.fetchone()[0]
        conn.close()
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Customers", total_customers)
        col2.metric("Total Accounts", total_accounts)
        col3.metric("Total Transactions", total_transactions)
        col4.metric("System Alerts", total_alerts)
        col5.metric("Locked Accounts", locked_accounts)
        st.markdown("---")
        st.markdown("### Admin Capabilities")
        st.markdown("""
            - Create, update, and delete customers
            - Manage savings and current accounts
            - Monitor deposits and withdrawals
            - Detect suspicious or high‑value transactions
            - Track all admin actions using audit logs
        """)
    else:
        st.markdown(f"### Welcome, {st.session_state.user_name}")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM accounts WHERE customer_id=?", (st.session_state.user_customer_id,))
        my_accounts = cur.fetchone()[0]
        cur.execute("SELECT IFNULL(SUM(balance),0) FROM accounts WHERE customer_id=?", (st.session_state.user_customer_id,))
        total_balance = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM transactions t
            JOIN accounts a ON t.account_number = a.account_number
            WHERE a.customer_id=?
        """, (st.session_state.user_customer_id,))
        my_transactions = cur.fetchone()[0]
        conn.close()
        col1, col2, col3 = st.columns(3)
        col1.metric("My Accounts", my_accounts)
        col2.metric("Total Balance", f"Rs. {total_balance}")
        col3.metric("Total Transactions", my_transactions)
        st.markdown("---")
        st.markdown("### Available Features")
        st.markdown("""
            - Open new bank accounts
            - Deposit and withdraw funds
            - Check account balance
            - View complete transaction history
        """)
    st.info("Security Notice: All sensitive operations are protected using role‑based access and are logged for audit and compliance purposes.")

# ADD CUSTOMER
elif menu == "Add Customer":
    st.subheader("Add Customer")
    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Full Name", placeholder="Enter full name")
        email = st.text_input("Email", placeholder="Enter email address")
        phone = st.text_input("Phone Number", max_chars=10, placeholder="10-digit phone")
        city = st.text_input("City", placeholder="Enter city")
        submit = st.form_submit_button("Add Customer")
    if submit:
        name, email, phone, city = name.strip(), email.strip(), phone.strip(), city.strip()
        if not name or not phone or not city:
            st.error("Full Name, Phone, and City cannot be empty")
        elif not phone.isdigit() or len(phone) != 10:
            st.error("Phone must be exactly 10 digits")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO customers (full_name, email, phone, city) VALUES (?,?,?,?)",
                            (name, email, phone, city))
                conn.commit()
                conn.close()
                st.success("Customer added successfully")
            except Exception as e:
                st.error(f"Error: {e}")

# VIEW CUSTOMERS
elif menu == "View Customers":
    st.subheader("Customer Details")
    with st.sidebar:
        st.markdown("### Filter")
        search = st.text_input("Search by Customer Name", placeholder="Type name...")
    conn = get_connection()
    cur = conn.cursor()
    if search.strip():
        cur.execute("SELECT customer_id, full_name, email, phone, city FROM customers WHERE full_name LIKE ? ORDER BY customer_id",
                    (f"%{search}%",))
    else:
        cur.execute("SELECT customer_id, full_name, email, phone, city FROM customers ORDER BY customer_id")
    rows = cur.fetchall()
    conn.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Customer ID", "Name", "Email", "Phone", "City"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No matching customers found")

# EDIT / DELETE CUSTOMERS
elif menu == "Edit / Delete Customers":
    st.subheader("Edit / Delete Customer")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id, full_name FROM customers ORDER BY full_name")
    customers = cur.fetchall()
    conn.close()
    if not customers:
        st.warning("No customers found. Please add a customer first.")
        st.stop()
    customer_options = {f"{row['full_name']} (ID: {row['customer_id']})": row['customer_id'] for row in customers}
    selected_customer = st.selectbox(
        "Select Customer to Edit/Delete",
        options=["-- Select --"] + list(customer_options.keys())
    )
    if selected_customer != "-- Select --":
        cust_id = customer_options[selected_customer]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE customer_id=?", (cust_id,))
        c = cur.fetchone()
        conn.close()
        if c:
            c = dict(c)
            st.markdown("### Update Customer")
            with st.form("update_customer_form"):
                name = st.text_input("Full Name", c["full_name"])
                email = st.text_input("Email", c["email"])
                phone = st.text_input("Phone", c["phone"])
                city = st.text_input("City", c["city"])
                update_btn = st.form_submit_button("Update")
            if update_btn:
                name, email, phone, city = name.strip(), email.strip(), phone.strip(), city.strip()
                if not name or not phone or not city:
                    st.error("Name, Phone, City required")
                elif not phone.isdigit() or len(phone) != 10:
                    st.error("Phone must be 10 digits")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE customers
                            SET full_name=?, email=?, phone=?, city=?
                            WHERE customer_id=?
                        """, (name, email, phone, city, c["customer_id"]))
                        conn.commit()
                        conn.close()
                        st.session_state.success_msg = "Customer updated"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update error: {e}")

            st.markdown("---")
            st.markdown("### Delete Customer")
            if st.button("Delete Customer"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM security_logs WHERE customer_id=?", (c["customer_id"],))
                    cur.execute("DELETE FROM alerts WHERE account_number IN (SELECT account_number FROM accounts WHERE customer_id=?)", (c["customer_id"],))
                    cur.execute("DELETE FROM transactions WHERE account_number IN (SELECT account_number FROM accounts WHERE customer_id=?)", (c["customer_id"],))
                    cur.execute("DELETE FROM accounts WHERE customer_id=?", (c["customer_id"],))
                    cur.execute("DELETE FROM customers WHERE customer_id=?", (c["customer_id"],))
                    conn.commit()
                    conn.close()
                    st.session_state.success_msg = "Customer and all related records deleted"
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete error: {e}")

# CREATE ACCOUNT
elif menu == "Create Account":
    st.subheader("Create Account")
    branch_options = [
        "Dasnagar", "Kona", "Balitikuri", "Amta",
        "Kolkata Main", "Salt Lake", "New Town", "Howrah",
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Pune", "Hyderabad"
    ]
    if st.session_state.role == "admin":
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT customer_id, full_name FROM customers ORDER BY full_name")
        customers = cur.fetchall()
        conn.close()
        if not customers:
            st.warning("No customers found. Please add a customer first.")
            st.stop()
        customer_options = {f"{row['full_name']} (ID: {row['customer_id']})": row['customer_id'] for row in customers}
        selected_customer = st.selectbox("Select Customer", options=list(customer_options.keys()))
        customer_id = customer_options[selected_customer]

        with st.form("admin_create_account_form"):
            branch = st.selectbox("Branch", branch_options)
            acc_type = st.selectbox("Account Type", ["savings", "current"])
            create_btn = st.form_submit_button("Create Account")
        if create_btn:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO accounts (customer_id, branch, account_type) VALUES (?,?,?)",
                            (customer_id, branch, acc_type))
                conn.commit()
                cur.execute("SELECT last_insert_rowid()")
                acc_no = cur.fetchone()[0]
                conn.close()
                st.success(f"Account created successfully! Account No: **{acc_no}**")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info(f"Creating account for **{st.session_state.user_name}**")
        with st.form("user_create_account_form"):
            branch = st.selectbox("Branch", branch_options)
            acc_type = st.selectbox("Account Type", ["savings", "current"])
            create_btn = st.form_submit_button("Create Account")
        if create_btn:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO accounts (customer_id, branch, account_type) VALUES (?,?,?)",
                            (st.session_state.user_customer_id, branch, acc_type))
                conn.commit()
                cur.execute("SELECT last_insert_rowid()")
                acc_no = cur.fetchone()[0]
                conn.close()
                st.success(f"Account created successfully! Account No: **{acc_no}**")
            except Exception as e:
                st.error(f"Error: {e}")

# VIEW ACCOUNTS
elif menu == "View Accounts":
    st.subheader("Account Details")
    with st.sidebar:
        st.markdown("### Filters")
        search = st.text_input("Search by Customer Name", placeholder="Type name...")
        branch_filter = st.selectbox("Branch", ["All", "Dasnagar", "Kona", "Balitikuri", "Amta", "Kolkata Main", "Salt Lake", "New Town", "Howrah", "Mumbai", "Delhi", "Bangalore", "Chennai", "Pune", "Hyderabad"])
        type_filter = st.selectbox("Account Type", ["All", "savings", "current"])
    conn = get_connection()
    cur = conn.cursor()
    if st.session_state.role == "admin":
        query = """
            SELECT a.account_number, c.full_name, a.account_type, a.branch, a.balance
            FROM accounts a JOIN customers c ON a.customer_id = c.customer_id WHERE 1=1
        """
        params = []
        if search.strip():
            query += " AND c.full_name LIKE ?"
            params.append(f"%{search}%")
        if branch_filter != "All":
            query += " AND a.branch = ?"
            params.append(branch_filter)
        if type_filter != "All":
            query += " AND a.account_type = ?"
            params.append(type_filter)
        cur.execute(query, params)
    else:
        cur.execute("""
            SELECT a.account_number, c.full_name, a.account_type, a.branch, a.balance
            FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
            WHERE a.customer_id=?
        """, (st.session_state.user_customer_id,))
    rows = cur.fetchall()
    conn.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Account No", "Customer", "Type", "Branch", "Balance"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No accounts found")

# EDIT / DELETE ACCOUNTS
elif menu == "Edit / Delete Accounts":
    st.subheader("Edit / Delete Account")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.account_number, c.full_name
        FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
        ORDER BY a.account_number
    """)
    accounts = cur.fetchall()
    conn.close()
    if not accounts:
        st.warning("No accounts found")
        st.stop()
    account_options = {f"{row['account_number']} - {row['full_name']}": row['account_number'] for row in accounts}
    selected_account = st.selectbox("Select Account", options=["-- Select --"] + list(account_options.keys()))
    if selected_account != "-- Select --":
        acc_no = account_options[selected_account]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.*, c.full_name FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
            WHERE a.account_number=?
        """, (acc_no,))
        a = cur.fetchone()
        conn.close()
        if a:
            a = dict(a)
            with st.form("edit_account_form"):
                st.text_input("Customer Name", a["full_name"], disabled=True)
                branch = st.selectbox("Branch", branch_options,
                                      index=branch_options.index(a["branch"]) if a["branch"] in branch_options else 0)
                acc_type = st.selectbox("Account Type", ["savings", "current"],
                                        index=0 if a["account_type"]=="savings" else 1)
                col1, col2 = st.columns(2)
                update_btn = col1.form_submit_button("Update")
                delete_btn = col2.form_submit_button("Delete")
            if update_btn:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE accounts SET branch=?, account_type=? WHERE account_number=?",
                                (branch, acc_type, a["account_number"]))
                    conn.commit()
                    conn.close()
                    st.session_state.success_msg = "Account updated"
                    st.rerun()
                except Exception as e:
                    st.error(f"Update error: {e}")
            if delete_btn:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM alerts WHERE account_number=?", (a["account_number"],))
                    cur.execute("DELETE FROM transactions WHERE account_number=?", (a["account_number"],))
                    cur.execute("DELETE FROM accounts WHERE account_number=?", (a["account_number"],))
                    conn.commit()
                    conn.close()
                    st.session_state.success_msg = "Account deleted"
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete error: {e}")

# DEPOSIT / WITHDRAW
elif menu == "Deposit / Withdraw":
    st.subheader("Deposit / Withdraw")
    conn = get_connection()
    cur = conn.cursor()
    if st.session_state.role == "admin":
        cur.execute("SELECT a.account_number, c.full_name FROM accounts a JOIN customers c ON a.customer_id = c.customer_id")
        rows = cur.fetchall()
        account_map = {f"{r[0]} - {r[1]}": r[0] for r in rows}
        display_list = ["Select"] + list(account_map.keys())
    else:
        cur.execute("SELECT account_number FROM accounts WHERE customer_id=?", (st.session_state.user_customer_id,))
        rows = cur.fetchall()
        display_list = ["Select"] + [r[0] for r in rows]
    cur.close()

    if len(display_list) == 1:
        st.warning("No accounts available")
        conn.close()
        st.stop()

    selected = st.selectbox("Account", display_list)
    if selected == "Select":
        conn.close()
        st.stop()

    if st.session_state.role == "admin":
        acc_no = account_map[selected]
    else:
        acc_no = selected

    cur = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE account_number=?", (acc_no,))
    balance = cur.fetchone()[0]
    cur.close()
    st.info(f"Current Balance: ₹{balance}")

    with st.form("txn_form"):
        txn_type = st.radio("Type", ["Deposit", "Withdraw"])
        amount = st.number_input("Amount", min_value=100.0, step=100.0)
        submit = st.form_submit_button("Submit")
    if submit:
        amount = Decimal(str(amount))
        if amount <= 0:
            st.error("Amount must be positive")
        else:
            try:
                perform_transaction(conn, acc_no, txn_type.lower(), float(amount))
                cur = conn.cursor()
                cur.execute("SELECT balance FROM accounts WHERE account_number=?", (acc_no,))
                new_balance = cur.fetchone()[0]
                cur.close()
                st.success(f"{txn_type} successful. New balance: ₹{new_balance}")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Transaction error: {e}")
    conn.close()

# CHECK BALANCE
elif menu == "Check Balance":
    st.subheader("Check Balance")
    conn = get_connection()
    cur = conn.cursor()
    if st.session_state.role == "admin":
        cur.execute("SELECT a.account_number, c.full_name FROM accounts a JOIN customers c ON a.customer_id = c.customer_id")
        rows = cur.fetchall()
        if not rows:
            st.warning("No accounts")
            conn.close()
            st.stop()
        account_map = {f"{r[0]} - {r[1]}": r[0] for r in rows}
        selected = st.selectbox("Select Account", ["Select"] + list(account_map.keys()))
        if selected != "Select":
            acc_no = account_map[selected]
            cur.execute("SELECT balance FROM accounts WHERE account_number=?", (acc_no,))
            balance = cur.fetchone()[0]
            st.success(f"Account Holder: {selected.split(' - ')[1]}\n\nBalance: ₹{balance}")
    else:
        cur.execute("SELECT account_number FROM accounts WHERE customer_id=?", (st.session_state.user_customer_id,))
        rows = cur.fetchall()
        if not rows:
            st.warning("No accounts")
            conn.close()
            st.stop()
        acc_no = st.selectbox("Select Account", [r[0] for r in rows])
        cur.execute("SELECT balance FROM accounts WHERE account_number=?", (acc_no,))
        balance = cur.fetchone()[0]
        st.success(f"Current Balance: ₹{balance}")
    conn.close()

# VIEW TRANSACTIONS
elif menu == "View Transactions":
    st.subheader("Transaction History")
    conn = get_connection()
    col1, col2, col3 = st.columns(3)
    if st.session_state.role == "admin":
        with col1:
            cur = conn.cursor()
            cur.execute("SELECT account_number FROM accounts")
            acc_list = [r[0] for r in cur.fetchall()]
            cur.close()
            selected_acc = st.selectbox("Account", ["All"] + acc_list)
    with col2:
        txn_filter = st.selectbox("Type", ["Both", "Deposit", "Withdraw"])
    with col3:
        date_filter = st.date_input("Date", value=None)

    query = """
        SELECT t.transaction_id, t.account_number, c.full_name, a.branch,
               t.transaction_type, t.amount, DATE(t.transaction_time) as txn_date, t.transaction_time
        FROM transactions t
        JOIN accounts a ON t.account_number = a.account_number
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE 1=1
    """
    params = []
    if st.session_state.role == "user":
        query += " AND a.customer_id = ?"
        params.append(st.session_state.user_customer_id)
    if st.session_state.role == "admin" and selected_acc != "All":
        query += " AND t.account_number = ?"
        params.append(selected_acc)
    if txn_filter != "Both":
        query += " AND t.transaction_type = ?"
        params.append(txn_filter.lower())
    if date_filter:
        query += " AND DATE(t.transaction_time) = ?"
        params.append(date_filter.isoformat())

    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Account No", "Customer", "Branch", "Type", "Amount", "Date", "Time"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No transactions found")
    if st.session_state.role == "admin":
        st.markdown("---")
        if st.checkbox("Show Branch-wise Total Balance"):
            cur = conn.cursor()
            cur.execute("SELECT branch, SUM(balance) FROM accounts GROUP BY branch")
            rows = cur.fetchall()
            cur.close()
            if rows:
                df2 = pd.DataFrame(rows, columns=["Branch", "Total Balance"])
                st.dataframe(df2, use_container_width=True)
    conn.close()

# VIEW ALERTS
elif menu == "View Alerts":
    st.subheader("High Value Transaction Alerts")
    conn = get_connection()
    col1, col2 = st.columns(2)
    with col1:
        alert_type = st.selectbox("Alert Type", ["Both", "Deposit", "Withdraw"])
    with col2:
        alert_date = st.date_input("Date", value=None)

    query = """
        SELECT a.alert_id, a.account_number, c.full_name, ac.branch,
               a.amount, a.message, DATE(a.alert_time) as alert_date, a.alert_time
        FROM alerts a
        JOIN accounts ac ON a.account_number = ac.account_number
        JOIN customers c ON ac.customer_id = c.customer_id
        WHERE 1=1
    """
    params = []
    if alert_type != "Both":
        query += " AND a.message LIKE ?"
        params.append(f"%{alert_type.lower()}%")
    if alert_date:
        query += " AND DATE(a.alert_time) = ?"
        params.append(alert_date.isoformat())

    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Alert ID", "Account No", "Customer", "Branch", "Amount", "Message", "Date", "Time"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No alerts found")

# ADMIN LOGS
elif menu == "Admin Logs":
    st.subheader("Admin Activity Logs")
    conn = get_connection()
    cur = conn.cursor()
    col1, col2, col3 = st.columns(3)
    with col1:
        op_filter = st.selectbox("Operation", ["All", "INSERT", "UPDATE", "DELETE"])
    with col2:
        start = st.date_input("Start Date", value=None)
    with col3:
        end = st.date_input("End Date", value=None)
    sort = st.radio("Sort", ["Descending", "Ascending"], horizontal=True)

    query = """
        SELECT log_id, table_name, operation_type, record_id, old_data, new_data, action_time
        FROM admin_logs
        WHERE 1=1
    """
    params = []
    if op_filter != "All":
        query += " AND operation_type = ?"
        params.append(op_filter)
    if start:
        query += " AND DATE(action_time) >= ?"
        params.append(start.isoformat())
    if end:
        query += " AND DATE(action_time) <= ?"
        params.append(end.isoformat())
    if sort == "Ascending":
        query += " ORDER BY log_id ASC"
    else:
        query += " ORDER BY log_id DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if rows:
        df = pd.DataFrame(rows, columns=["Log ID", "Table", "Operation", "Record ID", "Old Data", "New Data", "Date & Time"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No logs found")

# LOCKED ACCOUNTS
elif menu == "Locked Accounts":
    st.subheader("Locked User Accounts")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, full_name, email, failed_attempts, lock_until
        FROM customers
        WHERE lock_until IS NOT NULL AND lock_until > datetime('now')
        ORDER BY lock_until
    """)
    rows = cur.fetchall()
    if not rows:
        st.success("No locked accounts")
        conn.close()
        st.stop()
    df = pd.DataFrame(rows, columns=["ID", "Name", "Email", "Attempts", "Lock Until"])
    st.dataframe(df, use_container_width=True)
    st.markdown("---")
    st.markdown("### Unlock Account")
    locked_ids = [r["customer_id"] for r in rows]
    selected = st.selectbox("Select Customer ID", locked_ids)
    if st.button("Unlock"):
        try:
            cur.execute("UPDATE customers SET failed_attempts=0, lock_until=NULL WHERE customer_id=?", (selected,))
            conn.commit()
            st.success("Account unlocked")
            conn.close()
            st.rerun()
        except Exception as e:
            st.error(f"Unlock error: {e}")
    conn.close()

# SECURITY LOGS
elif menu == "Security Logs":
    st.subheader("Security Logs")
    conn = get_connection()
    col1, col2, col3 = st.columns(3)
    with col1:
        event_filter = st.selectbox("Event Type", ["All", "FAILED LOGIN", "ACCOUNT LOCKED", "ACCOUNT UNLOCKED"])
    with col2:
        start = st.date_input("Start Date", value=None)
    with col3:
        end = st.date_input("End Date", value=None)

    event_map = {"FAILED LOGIN": "FAILED_LOGIN", "ACCOUNT LOCKED": "ACCOUNT_LOCKED", "ACCOUNT UNLOCKED": "ACCOUNT_UNLOCKED"}
    query = """
        SELECT s.log_id, s.customer_id, c.full_name, s.event_type,
               s.failed_attempts, s.details, s.event_time
        FROM security_logs s
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE 1=1
    """
    params = []
    if event_filter != "All":
        query += " AND s.event_type = ?"
        params.append(event_map[event_filter])
    if start:
        query += " AND DATE(s.event_time) >= ?"
        params.append(start.isoformat())
    if end:
        query += " AND DATE(s.event_time) <= ?"
        params.append(end.isoformat())
    query += " ORDER BY s.event_time DESC"

    df = pd.read_sql_query(query, conn, params=params)
    if df.empty:
        st.info("No security logs found")
    else:
        df["event_type"] = df["event_type"].str.replace("_", " ")
        st.dataframe(df.rename(columns={
            "log_id": "Log ID", "customer_id": "Customer ID", "full_name": "Customer Name",
            "event_type": "Event", "failed_attempts": "Failed Attempts",
            "details": "Details", "event_time": "Timestamp"
        }), use_container_width=True)
    conn.close()

else:
    st.info("Please select an operation from the sidebar.")