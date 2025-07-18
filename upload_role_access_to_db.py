import pandas as pd
import sqlite3
import os

EXCEL_PATH = 'data/role_access.xlsx'
DB_PATH = 'db/bank_exchange.db'

def upload_role_access():
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Excel file not found: {EXCEL_PATH}")
        return
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        return
    df = pd.read_excel(EXCEL_PATH)
    conn = sqlite3.connect(DB_PATH)
    df.to_sql('role_access', conn, if_exists='replace', index=False)
    conn.close()
    print("✅ role_access table updated from Excel!")

if __name__ == "__main__":
    upload_role_access() 