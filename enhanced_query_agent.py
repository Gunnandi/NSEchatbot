import sqlite3
import pandas as pd
from enhanced_llm_interface import generate_sql_llm
from enhanced_embedding import SchemaEmbedder
import mysql.connector

def filter_sql_to_allowed(sql_query, allowed_tables, allowed_columns):
    # Basic check: only allow queries on allowed tables/columns
    # (For production, use SQL parsing for security)
    sql_lower = sql_query.lower()
    
    # Check if any allowed table is mentioned in the query
    table_found = False
    for table in allowed_tables:
        if table.lower() in sql_lower:
            table_found = True
            # If user has 'ALL' access to this table, allow it
            if allowed_columns.get(table) == 'ALL' or 'all' in str(allowed_columns.get(table, '')).lower():
                return True
            # Check if any allowed columns for this table are mentioned
            allowed_cols = allowed_columns.get(table, [])
            for col in allowed_cols:
                if col.lower() in sql_lower:
                    return True
    
    # If no specific tables found but user has access to tables, allow generic queries
    if allowed_tables and table_found:
        return True
    
    # For very generic queries (like SELECT * FROM table), allow if user has access to any table
    if allowed_tables and ('select' in sql_lower and 'from' in sql_lower):
        return True
        
    return False

def format_context_rows(context_rows):
    # Convert context rows (from SchemaEmbedder.search) to a string for LLM prompt
    if not context_rows:
        return ''
    lines = []
    for row in context_rows:
        if isinstance(row, pd.Series):
            lines.append(f"{row['Table']}.{row['Column']}: {row['Column Description']}")
        else:
            lines.append(str(row))
    return '\n'.join(lines)

def validate_sql(sql_query, allowed_tables, allowed_columns):
    """Validate SQL query before execution - dynamic schema validation. Strict: if any table or column is not in the allowed schema, auto-correct to closest match and inform the user, or return a user-facing error if no match."""
    if not sql_query:
        return False, "Empty SQL query"
    
    sql_lower = sql_query.lower()
    
    # Check for common SQLite syntax issues
    if 'interval' in sql_lower:
        return False, "SQLite doesn't support INTERVAL syntax. Use date('now', '-1 month') instead."
    
    if 'current_date' in sql_lower and 'interval' in sql_lower:
        return False, "Use date('now', '-1 month') for date arithmetic in SQLite."
    
    # Allow system queries (schema introspection)
    system_queries = [
        'sqlite_master',
        'pragma table_info',
        'pragma foreign_key_list',
        'pragma index_list'
    ]
    
    for sys_query in system_queries:
        if sys_query in sql_lower:
            return True, "System query allowed."
    
    # --- FLEXIBLE TABLE EXTRACTION ---
    import re
    import difflib
    table_pattern = r'\b(?:from|join|update|into)\s+`?([a-zA-Z0-9_]+)`?(?=\s|,|;|$)'
    mentioned_tables = re.findall(table_pattern, sql_query, re.IGNORECASE)
    mentioned_tables_norm = [t.lower().replace('`','').strip() for t in mentioned_tables]
    allowed_tables_norm = [t.lower().replace('`','').strip() for t in allowed_tables]
    table_corrections = {}
    # Check if all mentioned tables are allowed, else auto-correct
    invalid_tables = [table for table in mentioned_tables_norm if table not in allowed_tables_norm]
    if invalid_tables:
        suggestions = []
        for halluc in invalid_tables:
            close_matches = difflib.get_close_matches(halluc, allowed_tables_norm, n=1, cutoff=0.5)
            if close_matches:
                idx = allowed_tables_norm.index(close_matches[0])
                corrected = allowed_tables[idx]
                table_corrections[halluc] = corrected
                suggestions.append(f"'{halluc}' (auto-corrected to '{corrected}')")
            else:
                suggestions.append(f"'{halluc}' (no close match)")
        # If any hallucinated table has no close match, return error
        if any('(no close match)' in s for s in suggestions):
            return False, f"Your request could not be completed because the model tried to use table(s) {', '.join(suggestions)} which do not exist in your database. Please rephrase your question."
        # Otherwise, rewrite the query
        for halluc, corrected in table_corrections.items():
            sql_query = re.sub(rf'\b{halluc}\b', corrected, sql_query, flags=re.IGNORECASE)
        return 'corrected', f"The model tried to use table(s) {', '.join(suggestions)}. The query was auto-corrected to use your schema.", sql_query
    if not mentioned_tables_norm:
        return False, "No allowed tables found in query."
    # --- FLEXIBLE COLUMN EXTRACTION ---
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
    select_cols = []
    if select_match:
        select_cols_raw = select_match.group(1)
        select_cols = [c.strip().replace('`','') for c in select_cols_raw.split(',')]
    main_table = None
    if mentioned_tables_norm:
        idx = allowed_tables_norm.index(mentioned_tables_norm[0])
        main_table = allowed_tables[idx]
    column_corrections = {}
    for col in select_cols:
        if not col.strip():
            continue  # skip empty columns (e.g., from trailing comma)
        if '.' in col:
            table_part, col_part = col.split('.', 1)
            table_part = table_part.strip().lower()
            col_part = col_part.strip().lower()
            # Allow table.* wildcard
            if col_part == '*':
                continue
            actual_table = None
            for allowed_table in allowed_tables:
                if allowed_table.lower().replace('`','').strip() == table_part:
                    actual_table = allowed_table
                    break
            if not actual_table:
                return False, f"Your request could not be completed because the model tried to use table '{table_part}' which does not exist in your database. Please rephrase your question."
            allowed_cols = allowed_columns.get(actual_table, [])
            if allowed_cols != 'ALL':
                allowed_cols_lower = [c.lower().replace('`','').strip() for c in allowed_cols]
                if col_part not in allowed_cols_lower:
                    # Try to auto-correct
                    close_matches = difflib.get_close_matches(col_part, allowed_cols_lower, n=1, cutoff=0.5)
                    if close_matches:
                        idx = allowed_cols_lower.index(close_matches[0])
                        corrected = allowed_cols[idx]
                        column_corrections[(table_part, col_part)] = (actual_table, corrected)
                    else:
                        return False, f"Your request could not be completed because the model tried to use column '{col_part}' for table '{actual_table}', which does not exist in your database. Please rephrase your question."
        else:
            if col == '*':
                continue  # always allow SELECT *
            if main_table:
                allowed_cols = allowed_columns.get(main_table, [])
                if allowed_cols != 'ALL':
                    allowed_cols_lower = [c.lower().replace('`','').strip() for c in allowed_cols]
                    if col.lower() not in allowed_cols_lower:
                        # Try to auto-correct
                        close_matches = difflib.get_close_matches(col.lower(), allowed_cols_lower, n=1, cutoff=0.5)
                        if close_matches:
                            idx = allowed_cols_lower.index(close_matches[0])
                            corrected = allowed_cols[idx]
                            column_corrections[(main_table.lower(), col.lower())] = (main_table, corrected)
                        else:
                            return False, f"Your request could not be completed because the model tried to use column '{col}' for table '{main_table}', which does not exist in your database. Please rephrase your question."
    # If corrections needed, rewrite the query
    if table_corrections or column_corrections:
        for (table_part, col_part), (actual_table, corrected) in column_corrections.items():
            sql_query = re.sub(rf'{table_part}\.\s*{col_part}', f'{actual_table}.{corrected}', sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(rf'`?{table_part}`?\.\s*`?{col_part}`?', f'`{actual_table}`.`{corrected}`', sql_query, flags=re.IGNORECASE)
        return 'corrected', "The model tried to use non-existent columns. The query was auto-corrected to use your schema.", sql_query
    # Check for balanced parentheses
    if sql_query.count('(') != sql_query.count(')'):
        return False, "Unbalanced parentheses"
    if sql_lower.startswith('select'):
        if 'from' not in sql_lower:
            return False, "SELECT query missing FROM clause"
    invalid_chars = ['{', '}', '[', ']']
    for char in invalid_chars:
        if char in sql_query:
            return False, f"Invalid character '{char}' in SQL query"
    return True, "SQL validation passed."

def execute_sql_safely(sql_query, db_type, db_info):
    """Execute SQL query with better error handling for SQLite or MySQL"""
    conn = None
    try:
        if db_type == 'SQLite':
            conn = sqlite3.connect(db_info)
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA journal_mode = WAL")
            df = pd.read_sql_query(sql_query, conn)
        elif db_type == 'MySQL':
            conn = mysql.connector.connect(**db_info)
            df = pd.read_sql(sql_query, conn)
        else:
            return False, None, f"Unsupported DB type: {db_type}"
        conn.close()
        return True, df, None
    except Exception as e:
        if conn is not None:
            conn.close()
        return False, None, f"Unexpected error: {str(e)}"

class QueryAgent:
    def __init__(self, db_type, db_info, data_dict, role_access):
        self.db_type = db_type
        self.db_info = db_info
        self.data_dict = data_dict
        self.role_access = role_access
        # If data_dict is a DataFrame, pass it to SchemaEmbedder; else, use default path
        if isinstance(data_dict, pd.DataFrame):
            self.embedder = SchemaEmbedder(data_dict=data_dict)
        else:
            self.embedder = SchemaEmbedder('data/data_dictionary.xlsx')

    def get_connection(self):
        if self.db_type == 'SQLite':
            return sqlite3.connect(self.db_info)
        elif self.db_type == 'MySQL':
            return mysql.connector.connect(**self.db_info)
        else:
            raise ValueError('Unsupported DB type')

    def answer_query(self, question, allowed_tables, allowed_columns, previous_query=None, previous_result_columns=None):
        # RAG: Retrieve top-k relevant schema/context and data rows
        schema_results, data_row_results = self.embedder.search(question, top_k=5, data_row_k=3)
        rag_context = ''
        if schema_results:
            rag_context += '### RELEVANT SCHEMA CONTEXT\n' + format_context_rows(schema_results) + '\n'
        if data_row_results:
            rag_context += '\n### RELEVANT DATA ROWS (EXAMPLES)\n' + '\n'.join(str(r) for r in data_row_results) + '\n'
        
        # Use LLM to generate SQL with both full schema and RAG context
        sql_query_rag = generate_sql_llm(
            question, allowed_tables, allowed_columns, self.data_dict, rag_context=rag_context,
            previous_query=previous_query, previous_result_columns=previous_result_columns
        )
        sql_query_full = generate_sql_llm(
            question, allowed_tables, allowed_columns, self.data_dict,
            previous_query=previous_query, previous_result_columns=previous_result_columns
        )
        
        # Prefer RAG SQL if it uses relevant tables/columns
        sql_query = None
        if sql_query_rag and filter_sql_to_allowed(sql_query_rag, allowed_tables, allowed_columns):
            sql_query = sql_query_rag
        elif sql_query_full and filter_sql_to_allowed(sql_query_full, allowed_tables, allowed_columns):
            sql_query = sql_query_full
        
        if not sql_query:
            return None, "You are not allowed to access the requested data or the query could not be generated.", None
        
        # Validate SQL before execution
        val_result = validate_sql(sql_query, allowed_tables, allowed_columns)
        if isinstance(val_result, tuple) and len(val_result) == 3 and val_result[0] == 'corrected':
            # Auto-corrected query: use the corrected SQL and inform the user
            correction_msg = val_result[1]
            corrected_sql = val_result[2]
            # Validate the corrected SQL (should not recurse infinitely)
            is_valid2, validation_msg2 = validate_sql(corrected_sql, allowed_tables, allowed_columns)
            if is_valid2 is True:
                sql_query = corrected_sql
                validation_msg = correction_msg + ' ' + validation_msg2
            else:
                return corrected_sql, f"SQL validation failed after correction: {validation_msg2}", None
        else:
            is_valid = val_result[0]
            validation_msg = val_result[1]
            if not is_valid:
                return sql_query, f"SQL validation failed: {validation_msg}", None
        
        # Execute SQL with better error handling
        success, df, error_msg = execute_sql_safely(sql_query, self.db_type, self.db_info)
        
        if not success:
            return sql_query, f"Error executing SQL: {error_msg}", None
        
        # Build response
        response = self.generate_natural_response(question, df, sql_query)
        return sql_query, response, df

    def generate_natural_response(self, question, df, sql_query):
        if df is None or df.empty:
            return "I couldn't find any data matching your query."
        row_count = len(df)
        col_count = len(df.columns)
        response = f"I found {row_count} record(s) with {col_count} field(s) based on your query. "
        return response 