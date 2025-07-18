import sqlite3
import pandas as pd
import os
from datetime import datetime

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

DB_PATH = os.path.join('db', 'bank_exchange.db')

def get_table_info(table_name):
    """Get table structure and sample data"""
    conn = sqlite3.connect(DB_PATH)
    
    # Get table schema
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    # Get sample data (first 10 rows)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 10", conn)
    except:
        df = pd.DataFrame()
    
    conn.close()
    
    return columns, df

def create_table_excel(table_name, columns, sample_data):
    """Create Excel file for a table"""
    filename = f"data/{table_name}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Sheet 1: Table Structure
        structure_data = []
        for col in columns:
            cid, name, type_name, not_null, default_val, pk = col
            structure_data.append({
                'Column ID': cid,
                'Column Name': name,
                'Data Type': type_name,
                'Not Null': 'Yes' if not_null else 'No',
                'Default Value': default_val if default_val else 'None',
                'Primary Key': 'Yes' if pk else 'No'
            })
        
        structure_df = pd.DataFrame(structure_data)
        structure_df.to_excel(writer, sheet_name='Table Structure', index=False)
        
        # Sheet 2: Sample Data
        if not sample_data.empty:
            sample_data.to_excel(writer, sheet_name='Sample Data', index=False)
        else:
            pd.DataFrame({'Note': ['No data available']}).to_excel(writer, sheet_name='Sample Data', index=False)
        
        # Sheet 3: Table Info
        info_data = {
            'Property': ['Table Name', 'Total Columns', 'Sample Rows', 'Created Date'],
            'Value': [table_name, len(columns), len(sample_data), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        }
        info_df = pd.DataFrame(info_data)
        info_df.to_excel(writer, sheet_name='Table Info', index=False)
    
    print(f"Created {filename}")

def main():
    # List of all tables
    tables = [
        'USERS',
        'acct_mast',
        'amc_bank_dtl', 
        'amc_mast',
        'branch_mast',
        'card_mast',
        'cust_mast',
        'dept_mast',
        'emp_mast',
        'euin_mast',
        'loan_mast',
        'txn_hist'
    ]
    
    print("Creating Excel files for each table...")
    
    for table_name in tables:
        try:
            columns, sample_data = get_table_info(table_name)
            create_table_excel(table_name, columns, sample_data)
        except Exception as e:
            print(f"Error creating Excel for {table_name}: {e}")
    
    print("\nAll table Excel files created in the 'data' folder!")
    print("\nFiles created:")
    for table_name in tables:
        filename = f"data/{table_name}.xlsx"
        if os.path.exists(filename):
            print(f"✓ {filename}")

if __name__ == "__main__":
    main() 