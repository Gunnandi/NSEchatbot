import mysql.connector
import pandas as pd
import os

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"
MYSQL_DB = "bankexchange"
DATA_FOLDER = "data"

def create_db_from_excels():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()

    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".xlsx"):
            table_name = os.path.splitext(file)[0]
            df = pd.read_excel(os.path.join(DATA_FOLDER, file))
            # Create table if not exists (simple schema inference)
            columns = ', '.join([f'`{col}` VARCHAR(255)' for col in df.columns])
            cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table_name}` ({columns})")
            # Insert data
            for _, row in df.iterrows():
                placeholders = ', '.join(['%s'] * len(row))
                sql = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in df.columns])}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(row))
            print(f"✅ Loaded: {file} → table '{table_name}'")
    conn.commit()
    conn.close()
    print("🎉 All Excel files loaded into MySQL database")

if __name__ == "__main__":
    create_db_from_excels()
