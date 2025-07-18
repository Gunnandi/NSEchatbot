import mysql.connector
import pandas as pd
import os

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"
MYSQL_DB = "bankexchange"
DICT_PATH = os.path.join('data', 'data_dictionary.xlsx')

# Human-readable descriptions for tables and columns
TABLE_DESCRIPTIONS = {
    'cust_mast': 'Customer master table',
    'acct_mast': 'Account master table',
    'txn_hist': 'Transaction history',
    'emp_mast': 'Employee master table',
    'branch_mast': 'Branch master table',
    'dept_mast': 'Department master table',
    'card_mast': 'Card master table',
    'loan_mast': 'Loan master table',
    'amc_mast': 'Asset Management Company master',
    'amc_bank_dtl': 'AMC Bank Details',
    'euin_mast': 'Employee Unique Identification Number master',
}
COLUMN_DESCRIPTIONS = {
    'cust_id': 'Customer ID',
    'cust_name': 'Customer Name',
    'dob': 'Date of Birth',
    'address': 'Customer Address',
    'phone': 'Customer Phone Number',
    'acct_id': 'Account ID',
    'branch_id': 'Branch ID',
    'acct_type': 'Account Type',
    'open_date': 'Account Open Date',
    'balance': 'Account Balance',
    'txn_id': 'Transaction ID',
    'txn_date': 'Transaction Date',
    'amount': 'Transaction Amount',
    'txn_type': 'Transaction Type',
    'description': 'Transaction Description',
    'emp_id': 'Employee ID',
    'emp_name': 'Employee Name',
    'dept_id': 'Department ID',
    'dept_name': 'Department Name',
    'euin_no': 'Employee Unique Identification Number',
    'issue_date': 'Issue Date',
    'branch_name': 'Branch Name',
    'location': 'Branch Location',
    'card_id': 'Card ID',
    'card_type': 'Card Type',
    'expiry_date': 'Card Expiry Date',
    'status': 'Status',
    'loan_id': 'Loan ID',
    'amount': 'Loan Amount',
    'amc_id': 'AMC ID',
    'amc_name': 'AMC Name',
    'amc_bank_id': 'AMC Bank ID',
    'bank_name': 'Bank Name',
    'account_no': 'Bank Account Number',
    'ifsc_code': 'Bank IFSC Code',
}

def get_schema():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    schema = []
    for table_name in tables:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        for col in columns:
            col_name = col[0]
            schema.append({
                'Table': table_name,
                'Table Description': TABLE_DESCRIPTIONS.get(table_name, ''),
                'Column': col_name,
                'Column Description': COLUMN_DESCRIPTIONS.get(col_name, col_name.replace('_', ' ').title()),
                'Type': col[1],
                'PK': '✔' if col[3] == 'PRI' else '',
                'Foreign Key Table': '',  # MySQL foreign key extraction can be added if needed
                'Foreign Key Column': ''
            })
    conn.close()
    return schema

def main():
    schema = get_schema()
    df = pd.DataFrame(schema)
    df.to_excel(DICT_PATH, index=False)
    print(f"Data dictionary written to {DICT_PATH}")

if __name__ == "__main__":
    main() 