import mysql.connector
import os
from fpdf import FPDF

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"
MYSQL_DB = "bankexchange"
PDF_PATH = os.path.join('data', 'schema.pdf')

def get_schema_details():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    for table_name in tables:
        cursor.execute(f'SHOW COLUMNS FROM `{table_name}`')
        columns = cursor.fetchall()
        schema[table_name] = {'columns': columns, 'foreign_keys': []}
        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        create_stmt = cursor.fetchone()[1]
        for line in create_stmt.split('\n'):
            if 'FOREIGN KEY' in line:
                schema[table_name]['foreign_keys'].append(line.strip())
    conn.close()
    return schema

def create_pdf(schema):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Database Schema', ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('helvetica', '', 12)
    for table, details in schema.items():
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, f'Table: {table}', ln=True)
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(40, 8, 'Column', 1)
        pdf.cell(30, 8, 'Type', 1)
        pdf.cell(20, 8, 'PK', 1)
        pdf.cell(30, 8, 'Default', 1)
        pdf.cell(70, 8, 'Other', 1)
        pdf.ln()
        pdf.set_font('helvetica', '', 12)
        for col in details['columns']:
            pdf.cell(40, 8, str(col[0]), 1)
            pdf.cell(30, 8, str(col[1]), 1)
            pdf.cell(20, 8, 'Yes' if col[3] == 'PRI' else '', 1)
            pdf.cell(30, 8, str(col[4]) if col[4] else '', 1)
            pdf.cell(70, 8, '', 1)
            pdf.ln()
        if details['foreign_keys']:
            pdf.set_font('helvetica', 'I', 11)
            pdf.cell(0, 8, 'Foreign Keys:', ln=True)
            pdf.set_font('helvetica', '', 11)
            for fk in details['foreign_keys']:
                pdf.cell(0, 8, fk, ln=True)
        pdf.ln(5)
    try:
        pdf.output(PDF_PATH)
        print(f'Schema PDF written to {PDF_PATH}')
    except Exception as e:
        print(f'Error writing PDF: {e}')

def main():
    schema = get_schema_details()
    create_pdf(schema)

if __name__ == '__main__':
    main() 