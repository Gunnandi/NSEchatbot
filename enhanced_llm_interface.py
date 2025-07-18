import os
import requests
import json
import re
import sqlparse
import difflib

def clean_sql_response(sql, allowed_tables=None, allowed_columns=None, user_question=None):
    """Clean and validate SQL response from LLM. Only perform basic cleaning, plus a simple-table fallback for simple prompts."""
    if not sql:
        return None
    # Remove markdown formatting
    sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'^```\s*', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\s*```$', '', sql, flags=re.IGNORECASE)
    # Remove any non-SQL text before the query
    sql = re.sub(r'^.*?(SELECT|WITH|INSERT|UPDATE|DELETE)', r'\1', sql, flags=re.IGNORECASE | re.DOTALL)
    # Remove any text after the query
    sql = re.sub(r';\s*.*$', ';', sql, flags=re.DOTALL)
    # Clean up whitespace
    sql = re.sub(r'\s+', ' ', sql).strip()
    # Replace ILIKE with LIKE (SQLite does not support ILIKE)
    sql = re.sub(r'\bILIKE\b', 'LIKE', sql, flags=re.IGNORECASE)
    # Remove incomplete JOINs
    sql = re.sub(r'JOIN\s+[`\w]+\s+ON\s+[^=]+=\s*(;|$|\)|,|\s)', ' ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'JOIN\s+[`\w]+\s+ON\s+[^=]+=\s*([\'\"]{2}|NULL)', ' ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\s+', ' ', sql)
    # --- Simple-table fallback for simple prompts ---
    if user_question is not None and allowed_tables is not None and allowed_columns is not None:
        # Heuristic: if the user question is simple (e.g., 'show me all ...' or 'list all ...') and the query includes columns from more than one table, fallback
        simple_patterns = [r'^show me all', r'^list all', r'^show all', r'^display all', r'^give me all']
        if any(re.match(p, user_question.strip().lower()) for p in simple_patterns):
            # Extract all table.column references in SELECT
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
            if select_match:
                select_cols_raw = select_match.group(1)
                select_cols = [c.strip().replace('`','') for c in select_cols_raw.split(',')]
                tables_in_select = set()
                for col in select_cols:
                    if '.' in col:
                        t, _ = col.split('.', 1)
                        tables_in_select.add(t.strip())
                # If more than one table in SELECT, fallback
                if len(tables_in_select) > 1:
                    main_table = allowed_tables[0]
                    return f"SELECT * FROM `{main_table}`;"
    # Ensure it ends with semicolon
    if not sql.endswith(';'):
        sql += ';'
    return sql

def validate_sql_syntax(sql):
    """Basic SQL syntax validation"""
    if not sql:
        return False, "Empty SQL query"
    
    # Check for basic SQL structure
    sql_upper = sql.upper()
    
    # Must start with SELECT, WITH, INSERT, UPDATE, or DELETE
    if not any(sql_upper.startswith(keyword) for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE']):
        return False, "Query must start with SELECT, WITH, INSERT, UPDATE, or DELETE"
    
    # Check for balanced parentheses
    if sql.count('(') != sql.count(')'):
        return False, "Unbalanced parentheses"
    
    # Check for basic required keywords in SELECT queries
    if sql_upper.startswith('SELECT'):
        if 'FROM' not in sql_upper:
            return False, "SELECT query missing FROM clause"
    
    # Check for invalid characters that might cause syntax errors
    # Allow valid SQL operators but catch truly invalid characters
    invalid_chars = ['{', '}', '[', ']']
    for char in invalid_chars:
        if char in sql:
            return False, f"Invalid character '{char}' in SQL query"
    
    return True, "Valid SQL syntax"

def generate_sql_llm(question, allowed_tables, allowed_columns, data_dict, rag_context=None, previous_query=None, previous_result_columns=None):
    """
    Generate a SQL query from a user question using SQLCoder via Ollama.
    """
    try:
        # Ollama API endpoint
        OLLAMA_URL = "http://localhost:11434/api/generate"
        
        # --- COMPACT TABLE DICTIONARY CONTEXT ---
        table_dict_lines = []
        for table in allowed_tables:
            columns = allowed_columns.get(table, [])
            table_dict_lines.append(f"{table}: {', '.join(columns)}")
        table_dict_context = '\n'.join(table_dict_lines)
        
        # Create clear schema context with foreign keys (for reference, not at top)
        schema_lines = []
        for table in allowed_tables:
            columns = allowed_columns.get(table, [])
            schema_lines.append(f"Table `{table}` has columns: `{', '.join(columns)}`.")
            
            # Add foreign key info from data dictionary if available
            if data_dict is not None and not data_dict.empty:
                fk_info = data_dict[(data_dict['Table'] == table) & (data_dict['Foreign Key Table'].notna())]
                if not fk_info.empty:
                    fks = []
                    for _, row in fk_info.iterrows():
                        fks.append(f"`{row['Column']}` -> `{row['Foreign Key Table']}`.`{row['Foreign Key Column']}`")
                    schema_lines.append(f"  - Foreign Keys: {'; '.join(fks)}")
                
                # Add table description if available
                table_desc = data_dict[data_dict['Table'] == table]['Table Description'].iloc[0] if not data_dict[data_dict['Table'] == table].empty else ""
                if table_desc:
                    schema_lines.append(f"  - Description: {table_desc}")
            
            schema_lines.append("")

        schema_context = '\n'.join(schema_lines)
        
        # --- FEW-SHOT EXAMPLES ---
        few_shot_examples = '''
### EXAMPLE 1
DATABASE SCHEMA
Table `customers` has columns: `customer_id`, `name`, `dob`, `address`.
Table `accounts` has columns: `account_id`, `customer_id`, `balance`, `open_date`.

USER QUESTION
List the names and addresses of all customers.

SQL QUERY (ONLY THE QUERY, NO EXPLANATIONS)
SELECT `name`, `address` FROM `customers`;

### EXAMPLE 2
DATABASE SCHEMA
Table `transactions` has columns: `txn_id`, `account_id`, `amount`, `txn_date`.
Table `accounts` has columns: `account_id`, `customer_id`, `balance`, `open_date`.

USER QUESTION
Show the total transaction amount for each account.

SQL QUERY (ONLY THE QUERY, NO EXPLANATIONS)
SELECT `account_id`, SUM(`amount`) as total_amount FROM `transactions` GROUP BY `account_id`;

### EXAMPLE 3 (BAD)
DATABASE SCHEMA
Table `txn_hist` has columns: `txn_id`, `acct_id`, `amount`, `txn_type`.
Table `acct_mast` has columns: `acct_id`, `cust_id`, `acct_type`.

USER QUESTION
Show me all transactions.

BAD SQL QUERY (DO NOT DO THIS)
SELECT txn_hist.txn_id, acct_mast.acct_type FROM txn_hist JOIN acct_mast ON txn_hist.acct_id = acct_mast.acct_id;

GOOD SQL QUERY
SELECT * FROM txn_hist;
'''

        # --- PREVIOUS QUERY/RESULT CONTEXT ---
        previous_context = ""
        if previous_query:
            previous_context += f"\n### PREVIOUS QUERY\n{previous_query}\n"
        if previous_result_columns:
            if isinstance(previous_result_columns, (list, tuple)):
                col_str = ', '.join(previous_result_columns)
            else:
                col_str = str(previous_result_columns)
            previous_context += f"\n### PREVIOUS RESULT COLUMNS\n{col_str}\n"

        # --- Available tables list ---
        available_tables_str = ', '.join(allowed_tables)
        # Enhanced prompt with compact schema context at the top and strong rule
        prompt = f"""
### TABLES AND COLUMNS (USE ONLY THESE):
{table_dict_context}

You MUST use only the table names and column names listed above. If you use any other table or column, your answer will be rejected.

### CRITICAL RULES:
1. Output ONLY the SQL query - no explanations, no markdown, no extra text
2. Use ONLY the provided table and column names - NEVER invent or guess table or column names
3. Use valid SQLite syntax only
4. Use backticks for table and column names: `table_name`.`column_name`
5. Always prefer the simplest possible query that answers the question. If a single-table query suffices, do not use multiple tables.
6. Do NOT use JOINs, subqueries, or advanced SQL unless the question clearly requires data from multiple tables or complex logic.
7. Avoid GROUP BY, HAVING, or window functions unless the question asks for aggregation or grouping.
8. Use aggregations (AVG, SUM, COUNT, etc.) only if the question requires it.
9. For date filtering, use: WHERE date_column >= date('now', '-1 month')
10. For comparisons, use: WHERE column > 50000 or WHERE column < 1000
11. Always end with semicolon
12. CAREFULLY read the data dictionary and schema to understand what is required and what is available. Do not invent columns or tables.
13. For case-insensitive matching, use LIKE (SQLite does not support ILIKE). If you need to ensure case-insensitivity, use LOWER(column) LIKE ...
14. For extracting year, month, or day from a date in SQLite, use strftime('%Y', date_column) for year, strftime('%m', date_column) for month, etc. Do NOT use to_char, to_number, extract, or date_part.
15. For date parsing and filtering in SQLite, use the date string format 'YYYY-MM-DD' directly. Do NOT use to_date, cast, or convert functions. For date ranges, use WHERE date_column BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'.
16. ONLY use table and column names that are explicitly listed in the provided schema and data dictionary. NEVER invent or guess table or column names.
17. If a column or table is not present in the schema, do NOT use it in the query.
18. If the question is ambiguous, generate a simple query using the most relevant table and columns from the schema.
19. STRICT SCHEMA ADHERENCE: You can ONLY use tables and columns that are explicitly provided. Any table or column not in the schema is FORBIDDEN.
20. NO HALLUCINATION: Do not create, invent, or assume the existence of any tables or columns not explicitly listed.
21. Do NOT use JOINs unless the question explicitly requires data from multiple tables. If the question only asks about one table, use only that table.
22. **WARNING: If you use a table or column not in the schema, your answer will be rejected.**
23. If the user's question can be answered from a single table, use only that table and do not include columns from other tables.

### DATABASE SCHEMA (REFERENCE)
{schema_context}

{few_shot_examples}
{previous_context}
### RAG CONTEXT (Additional relevant context)
{rag_context if rag_context else "No additional context."}

### USER QUESTION
{question}

### SQL QUERY (ONLY THE QUERY, NO EXPLANATIONS)
"""
        
        # Prepare request for Ollama
        payload = {
            "model": "sqlcoder",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.9,
                "num_predict": 256,
                "stop": ["\n\n", "###", "Explanation:", "Here's", "The query"]
            }
        }
        
        # Make request to Ollama
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            sql = result.get('response', '').strip()
            
            # Clean the SQL response
            sql = clean_sql_response(sql, allowed_tables, allowed_columns, question)
            
            # Validate SQL syntax
            is_valid, validation_msg = validate_sql_syntax(sql)
            
            if is_valid:
                return sql
            else:
                print(f"Generated SQL failed validation: {validation_msg}")
                print(f"Raw SQL: {sql}")
                # Fall back to simple query generation
                return generate_simple_sql(question, allowed_tables, allowed_columns)
        else:
            print(f"Ollama API error: {response.status_code} - {response.text}")
            raise Exception(f"Ollama API returned status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama. Make sure Ollama is running and the sqlcoder model is installed.")
        print("To install sqlcoder: ollama pull sqlcoder")
        raise Exception("Ollama connection failed. Please ensure Ollama is running and sqlcoder model is installed.")
    except Exception as e:
        print(f"LLM Error: {e}")
        return generate_simple_sql(question, allowed_tables, allowed_columns)

def generate_simple_sql(question, allowed_tables, allowed_columns):
    """Generate a simple fallback SQL query when LLM fails"""
    if not allowed_tables:
        return None
    
    # Choose the first available table
    table = allowed_tables[0]
    columns = allowed_columns.get(table, [])
    
    # Extract key terms from the question
    question_lower = question.lower()
    
    # Check for aggregation keywords
    if any(word in question_lower for word in ['average', 'avg', 'mean']):
        if columns and len(columns) > 1:
            # Use the second column for aggregation if available
            agg_column = columns[1] if len(columns) > 1 else columns[0]
            return f"SELECT AVG(`{agg_column}`) as average_value FROM `{table}`;"
    
    if any(word in question_lower for word in ['count', 'total', 'number']):
        return f"SELECT COUNT(*) as total_count FROM `{table}`;"