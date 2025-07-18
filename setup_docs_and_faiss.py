# setup_docs_and_faiss.py
import os
import sqlite3
import json
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

# --- Configuration ---
DB_PATH = "business.db"  # Path to your SQLite DB created by create_bank_exchange_db.py
FAISS_INDEX_DIR = "embeddings"
FAISS_INDEX_PATH = Path(FAISS_INDEX_DIR) / "faiss.index"
META_FILE_PATH = Path(FAISS_INDEX_DIR) / "faiss.index.meta.json"
EMBED_MODEL = "all-MiniLM-L6-v2"  # Good general-purpose embedding model
DATA_FOLDER = "data"

def extract_schema_and_metadata_from_db(db_path):
    """
    Extracts table schema, column descriptions (from data_dictionary),
    and relationships from the SQLite database and Excel files.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    chunks = []

    try:
        # Load data dictionary from Excel file
        data_dictionary_path = os.path.join(DATA_FOLDER, "data_dictionary.xlsx")
        if os.path.exists(data_dictionary_path):
            data_dictionary_df = pd.read_excel(data_dictionary_path)
            print(f"✅ Loaded data dictionary from {data_dictionary_path}")
        else:
            print(f"⚠️ Data dictionary not found at {data_dictionary_path}")
            data_dictionary_df = pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading data dictionary: {e}")
        data_dictionary_df = pd.DataFrame()

    # Get all table names from the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        # 1. Add table description and column definitions from data_dictionary
        table_info = f"Table: {table_name}\n"
        
        # Get column descriptions for this table from data dictionary
        if not data_dictionary_df.empty and 'TableName' in data_dictionary_df.columns:
            table_cols_dd = data_dictionary_df[data_dictionary_df['TableName'] == table_name]
            for _, row in table_cols_dd.iterrows():
                if 'ColumnName' in row and 'Description' in row:
                    table_info += f"  Column '{row['ColumnName']}': {row['Description']}\n"
        
        # 2. Get actual schema information from the database
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        table_info += "  Schema:\n"
        for col in columns:
            cid, name, type_name, not_null, default_val, pk = col
            constraints = []
            if pk:
                constraints.append("PRIMARY KEY")
            if not_null:
                constraints.append("NOT NULL")
            if default_val:
                constraints.append(f"DEFAULT {default_val}")
            
            constraint_str = f" ({', '.join(constraints)})" if constraints else ""
            table_info += f"    {name} {type_name}{constraint_str}\n"
        
        # 3. Get foreign key relationships
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        
        if foreign_keys:
            table_info += "  Foreign Keys:\n"
            for fk in foreign_keys:
                id, seq, table, from_col, to_col, on_update, on_delete, match = fk
                table_info += f"    {from_col} → {table}.{to_col}\n"
        
        # 4. Get sample data (first 3 rows) for context
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            if sample_data:
                table_info += "  Sample Data:\n"
                for row in sample_data:
                    table_info += f"    {row}\n"
        except Exception as e:
            table_info += f"  Sample Data: Error retrieving data - {e}\n"
        
        chunks.append(table_info.strip())

    conn.close()
    return chunks

def extract_excel_table_info():
    """
    Extract additional information from individual table Excel files
    """
    chunks = []
    
    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".xlsx") and file != "data_dictionary.xlsx" and file != "role_access.xlsx":
            table_name = os.path.splitext(file)[0]
            excel_path = os.path.join(DATA_FOLDER, file)
            
            try:
                # Read all sheets from the Excel file
                excel_file = pd.ExcelFile(excel_path)
                
                excel_info = f"Excel File: {file}\nTable: {table_name}\n"
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_path, sheet_name=sheet_name)
                    excel_info += f"\nSheet: {sheet_name}\n"
                    excel_info += f"Columns: {list(df.columns)}\n"
                    excel_info += f"Rows: {len(df)}\n"
                    
                    if sheet_name == "Table Structure":
                        excel_info += "Structure:\n"
                        for _, row in df.iterrows():
                            excel_info += f"  {row.to_dict()}\n"
                    elif sheet_name == "Sample Data" and len(df) > 0:
                        excel_info += "Sample Data:\n"
                        for _, row in df.head(2).iterrows():
                            excel_info += f"  {row.to_dict()}\n"
                
                chunks.append(excel_info.strip())
                
            except Exception as e:
                print(f"❌ Error processing {file}: {e}")
    
    return chunks

def create_faiss_index(chunks, index_path, meta_path, model_name=EMBED_MODEL):
    """
    Creates and saves a FAISS index from text chunks.
    Also saves the original chunks to a meta file for retrieval.
    """
    print("🔍 Embedding text using SentenceTransformer...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks)

    # FAISS index creation
    # IndexFlatL2 is a simple Euclidean distance index
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    # Create directory if it doesn't exist
    index_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the FAISS index
    faiss.write_index(index, str(index_path))

    # Save the original chunks (metadata) for later retrieval based on index ID
    with open(meta_path, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"✅ FAISS index created and saved at {index_path}")
    print(f"📦 {len(chunks)} chunks embedded.")

def main():
    print("🗃️ Extracting database schema and metadata for RAG context...")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database {DB_PATH} not found. Please run create_bank_exchange_db.py first.")
        return
    
    # Extract database schema and metadata
    db_context_chunks = extract_schema_and_metadata_from_db(DB_PATH)
    
    # Extract Excel file information
    excel_chunks = extract_excel_table_info()
    
    # Combine all chunks
    all_chunks = db_context_chunks + excel_chunks

    if not all_chunks:
        print("🔴 No context chunks were extracted. FAISS index will not be created.")
        return

    print(f"📊 Extracted {len(db_context_chunks)} database chunks and {len(excel_chunks)} Excel chunks")
    
    create_faiss_index(all_chunks, FAISS_INDEX_PATH, META_FILE_PATH, EMBED_MODEL)
    print("\n✅ FAISS setup complete. You can now run your RAG SQL chatbot app.")

if __name__ == "__main__":
    main()

