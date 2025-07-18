from sentence_transformers import SentenceTransformer, util
import pandas as pd
import numpy as np
import os
import mysql.connector

# Try to use local embedding model, fallback to smaller model that can be cached
def get_embedding_model():
    # Check for local embedding models in models folder
    models_dir = 'models'
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.lower().find('embedding') != -1 or f.lower().find('sentence') != -1:
                return os.path.join(models_dir, f)
    
    # Fallback to a smaller model that will be cached locally
    return 'all-MiniLM-L6-v2'  # This will be cached after first download

EMBED_MODEL = get_embedding_model()

class SchemaEmbedder:
    def __init__(self, data_dict_path='data/data_dictionary.xlsx', data_dict=None, embed_data_rows=True):
        try:
            self.model = SentenceTransformer(EMBED_MODEL)
            print(f"Using embedding model: {EMBED_MODEL}")
        except Exception as e:
            print(f"Warning: Could not load embedding model {EMBED_MODEL}: {e}")
            print("Falling back to basic text matching")
            self.model = None
        if data_dict is not None:
            self.data_dict = data_dict
        else:
            self.data_dict = pd.read_excel(data_dict_path) if os.path.exists(data_dict_path) else pd.DataFrame()
        self.embeddings = None
        self.texts = []
        self.data_row_texts = []
        self.data_row_embeddings = None
        # Compute embeddings once during initialization
        if not self.data_dict.empty and self.model is not None:
            self._embed_schema()
        if embed_data_rows and self.model is not None:
            self._embed_data_rows()

    def _embed_schema(self):
        """Compute embeddings once and cache them"""
        if self.model is None:
            return
        self.texts = [f"{row['Table']} {row['Column']} {row['Column Description']}" for _, row in self.data_dict.iterrows()]
        if self.texts:
            self.embeddings = self.model.encode(self.texts, convert_to_tensor=True)
            print(f"Embedded {len(self.texts)} schema items (cached for reuse)")

    def _embed_data_rows(self, max_rows_per_table=1000):
        """Embed all rows from all tables in the MySQL database (up to max_rows_per_table per table)"""
        try:
            conn = mysql.connector.connect(
                host='localhost', user='root', password='password', database='bankexchange'
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] if isinstance(row, (list, tuple)) else list(row)[0] for row in cursor.fetchall()]
            data_row_texts = []
            for table in tables:
                df = pd.read_sql(f'SELECT * FROM `{table}` LIMIT {max_rows_per_table}', conn)
                for _, row in df.iterrows():
                    row_str = f"table: {table} | " + ' | '.join([f"{col}: {row[col]}" for col in df.columns])
                    data_row_texts.append(row_str)
            self.data_row_texts = data_row_texts
            if self.data_row_texts and self.model is not None:
                self.data_row_embeddings = self.model.encode(self.data_row_texts, convert_to_tensor=True)
                print(f"Embedded {len(self.data_row_texts)} data rows (cached for reuse)")
            conn.close()
        except Exception as e:
            print(f"Warning: Could not embed data rows from MySQL: {e}")
            self.data_row_texts = []
            self.data_row_embeddings = None

    def search(self, question, top_k=5, data_row_k=3):
        """Search using cached schema and data row embeddings - no recomputation needed"""
        schema_results = []
        data_row_results = []
        if self.model is None or self.embeddings is None or self.data_dict.empty:
            # Fallback to basic text matching if no embeddings
            schema_results = self._basic_search(question, top_k)
        else:
            q_emb = self.model.encode([question], convert_to_tensor=True)
            hits = util.semantic_search(q_emb, self.embeddings, top_k=top_k)[0]
            schema_results = [self.data_dict.iloc[int(hit['corpus_id'])] for hit in hits]
        # Data row search
        if self.model is not None and self.data_row_embeddings is not None and self.data_row_texts:
            q_emb = self.model.encode([question], convert_to_tensor=True)
            hits = util.semantic_search(q_emb, self.data_row_embeddings, top_k=data_row_k)[0]
            data_row_results = [self.data_row_texts[int(hit['corpus_id'])] for hit in hits]
        return schema_results, data_row_results
    
    def _basic_search(self, question, top_k=5):
        """Fallback search using basic text matching"""
        if self.data_dict.empty:
            return []
        question_lower = question.lower()
        scores = []
        for idx, row in self.data_dict.iterrows():
            text = f"{row['Table']} {row['Column']} {row['Column Description']}".lower()
            score = sum(1 for word in question_lower.split() if word in text)
            scores.append((score, idx))
        scores.sort(reverse=True)
        return [self.data_dict.iloc[idx] for score, idx in scores[:top_k] if score > 0] 