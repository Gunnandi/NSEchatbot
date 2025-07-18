import pandas as pd
import os
import mysql.connector
import hashlib

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"
MYSQL_DB = "bankexchange"
EXCEL_PATH = os.path.join('data', 'role_access.xlsx')

ROLES = ['Teller', 'Manager', 'Auditor', 'IT', 'Customer Service']

def get_tables_and_columns():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    table_cols = {}
    for table_name in tables:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        table_cols[table_name] = [col[0] for col in columns]
    conn.close()
    return table_cols

def build_access_matrix(table_cols):
    # Define access per role (example realistic policy)
    access = {
        'Teller': {
            'cust_mast': 'cust_id,cust_name,phone',
            'acct_mast': 'acct_id,cust_id,acct_type,balance',
            'txn_hist': 'ALL',
            'emp_mast': '',
            'branch_mast': '',
            'dept_mast': '',
            'card_mast': 'acct_id,card_id,card_type,status',
            'loan_mast': '',
            'amc_mast': '',
            'amc_bank_dtl': '',
            'euin_mast': '',
        },
        'Manager': {t: 'ALL' for t in table_cols},
        'Auditor': {t: 'ALL' for t in table_cols},
        'IT': {t: 'ALL' for t in table_cols},
        'Customer Service': {
            'cust_mast': 'cust_id,cust_name,phone,address',
            'acct_mast': 'acct_id,cust_id,acct_type,balance',
            'txn_hist': '',
            'emp_mast': '',
            'branch_mast': '',
            'dept_mast': '',
            'card_mast': 'acct_id,card_id,card_type,status',
            'loan_mast': '',
            'amc_mast': '',
            'amc_bank_dtl': '',
            'euin_mast': '',
        },
    }
    # Fill missing tables for each role with ''
    for role in ROLES:
        for t in table_cols:
            if t not in access[role]:
                access[role][t] = ''
    # Build DataFrame
    df = pd.DataFrame.from_dict(access, orient='index')
    df = df[sorted(df.columns)]
    return df

def save_to_db(df):
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    df.reset_index(names=['role_name'], inplace=True)
    # Create table
    columns = ', '.join([f'`{col}` VARCHAR(255)' for col in df.columns])
    cursor.execute(f"CREATE TABLE IF NOT EXISTS role_access ({columns})")
    # Insert data
    for _, row in df.iterrows():
        placeholders = ', '.join(['%s'] * len(row))
        sql = f"INSERT INTO role_access ({', '.join([f'`{col}`' for col in df.columns])}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(row))
    conn.commit()
    conn.close()

def main():
    table_cols = get_tables_and_columns()
    df = build_access_matrix(table_cols)
    df.to_excel(EXCEL_PATH)
    save_to_db(df.copy())
    print(f'Role access matrix written to {EXCEL_PATH}')

def authenticate(username, password):
    # Simple authentication for demo
    if username.lower() in ['teller', 'manager', 'auditor', 'it', 'customer service']:
        if password == f"{username.lower()}123":
            return username.title()
    return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_user_role(username, db_path):
    # This function is no longer relevant as role access is stored in MySQL
    # Keeping it for now, but it will always return None
    return None

def load_role_access():
    if os.path.exists(EXCEL_PATH):
        return pd.read_excel(EXCEL_PATH, index_col=0)
    return pd.DataFrame()

def get_allowed_tables(role, role_access):
    if role_access is not None and role in role_access.index:
        allowed = role_access.loc[role]
        # Get tables with non-empty access
        return [table for table, access in allowed.items() if str(access).strip()]
    return []

def get_allowed_columns(role, table, role_access, table_cols):
    if role_access is not None and role in role_access.index:
        allowed = role_access.loc[role]
        val = allowed.get(table, '')
        if isinstance(val, str):
            if val.strip().upper() == 'ALL':
                return table_cols.get(table, [])
            elif val.strip():
                return [c.strip() for c in val.split(',') if c.strip()]
    return []

if __name__ == "__main__":
    main()
