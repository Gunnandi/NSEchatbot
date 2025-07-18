# Technical Project Overview

## 🏗️ System Architecture Deep Dive

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│  Streamlit Web App (enhanced_app.py)                            │
│  • Role-based authentication                                    │
│  • Dynamic UI components                                        │
│  • Real-time query processing                                   │
│  • Results visualization                                        │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LOGIC LAYER                    │
├─────────────────────────────────────────────────────────────────┤
│  Query Agent (enhanced_query_agent.py)                          │
│  • Query orchestration                                          │
│  • RAG context retrieval                                        │
│  • SQL validation & security                                    │
│  • Response generation                                          │
│                                                                  │
│  LLM Interface (enhanced_llm_interface.py)                      │
│  • Model management                                             │
│  • Schema-aware prompting                                       │
│  • SQL generation                                               │
│  • Error handling                                               │
│                                                                  │
│  Embedding System (enhanced_embedding.py)                       │
│  • Semantic search                                              │
│  • Context retrieval                                            │
│  • Embedding caching                                            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  SQLite Database (bank_exchange.db)                             │
│  • 10 tables with relationships                                 │
│  • 1000+ synthetic records                                      │
│  • Foreign key constraints                                      │
│                                                                  │
│  Configuration Files                                             │
│  • data_dictionary.xlsx (schema docs)                           │
│  • role_access.xlsx (permissions)                               │
│  • schema.pdf (documentation)                                   │
│  • er_diagram.jpeg (visualization)                              │
│                                                                  │
│  AI Models                                                       │
│  • sqlcoder (via Ollama) - SQL generation                      │
│  • all-MiniLM-L6-v2 (RAG context)                              │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Architecture

### 1. User Query Processing Flow

```
User Input → Authentication → Schema Loading → RAG Retrieval → LLM Generation → Validation → Execution → Response
     │              │              │              │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼              ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Natural  │   │Role     │   │Allowed  │   │Schema   │   │SQL      │   │Security │   │Database │   │Formatted│
│Language │   │Check    │   │Tables   │   │Context  │   │Query    │   │Validate │   │Query    │   │Results  │
│Question │   │         │   │Columns  │   │         │   │         │   │         │   │         │   │         │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### 2. Detailed Component Interactions

#### A. Authentication & Authorization Flow
```python
# 1. User selects role
role = st.selectbox("Select Role", ["Teller", "Manager", "Auditor", "IT", "Customer Service"])

# 2. Load role permissions
role_access = pd.read_excel('data/role_access.xlsx', index_col=0)
allowed_tables = get_allowed_tables(role, role_access)

# 3. Get column-level permissions
for table in allowed_tables:
    allowed_columns[table] = get_allowed_columns(role, table, role_access, table_cols)
```

#### B. RAG Context Retrieval Flow
```python
# 1. User question analysis
question = "Find customers who have both savings and checking accounts"

# 2. Semantic search for relevant schema
embedder = SchemaEmbedder('data/data_dictionary.xlsx')
rag_context_rows = embedder.search(question, top_k=5)

# 3. Context formatting
rag_context = format_context_rows(rag_context_rows)
# Output: "cust_mast.cust_id: Customer unique identifier\nacct_mast.acct_type: Account type..."
```

#### C. LLM SQL Generation Flow
```python
# 1. Schema context creation
schema_context = f"Table: cust_mast\nColumns: cust_id, cust_name, dob, address, phone\n\nTable: acct_mast\nColumns: acct_id, cust_id, branch_id, acct_type, open_date, balance"

# 2. LLM prompt construction
prompt = f"""You are SQLCoder, an expert SQL generator for SQLite databases.
Schema: {schema_context}
Question: {question}
Generate ONLY the SQL query:"""

# 3. Model execution
llm = Llama(model_path=sqlcoder_path, n_ctx=2048, n_threads=4)
sql = llm(prompt, max_tokens=256, stop=[";", "\n"])
```

#### D. Validation & Execution Flow
```python
# 1. SQL validation
is_valid, validation_msg = validate_sql(sql_query, allowed_tables, allowed_columns)

# 2. Security filtering
if filter_sql_to_allowed(sql_query, allowed_tables, allowed_columns):
    # 3. Database execution
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql_query, conn)
    conn.close()
```

## 📊 Database Schema Design

### Entity Relationship Model

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  cust_mast  │    │  acct_mast  │    │  txn_hist   │
│             │    │             │    │             │
│ cust_id (PK)│◄───┤ cust_id (FK)│◄───┤ acct_id (FK)│
│ cust_name   │    │ acct_id (PK)│    │ txn_id (PK) │
│ dob         │    │ branch_id   │    │ txn_date    │
│ address     │    │ acct_type   │    │ amount      │
│ phone       │    │ open_date   │    │ txn_type    │
└─────────────┘    │ balance     │    │ description │
                   └─────────────┘    └─────────────┘
                            │
                            ▼
                   ┌─────────────┐
                   │ branch_mast │
                   │             │
                   │ branch_id   │
                   │ branch_name │
                   │ location    │
                   └─────────────┘
```

### Table Relationships

| Table | Primary Key | Foreign Keys | Relationships |
|-------|-------------|--------------|---------------|
| `cust_mast` | `cust_id` | None | Parent to `acct_mast`, `loan_mast` |
| `acct_mast` | `acct_id` | `cust_id`, `branch_id` | Child of `cust_mast`, `branch_mast`; Parent to `txn_hist`, `card_mast` |
| `txn_hist` | `txn_id` | `acct_id` | Child of `acct_mast` |
| `branch_mast` | `branch_id` | None | Parent to `acct_mast`, `emp_mast`, `loan_mast` |
| `emp_mast` | `emp_id` | `dept_id`, `branch_id` | Child of `dept_mast`, `branch_mast` |
| `dept_mast` | `dept_id` | None | Parent to `emp_mast` |
| `loan_mast` | `loan_id` | `cust_id`, `branch_id` | Child of `cust_mast`, `branch_mast` |
| `card_mast` | `card_id` | `acct_id` | Child of `acct_mast` |

## 🔐 Security Architecture

### Multi-Layer Security Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Authentication                                        │
│  • Role-based user selection                                    │
│  • Session management                                           │
│  • Access logging                                               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Authorization                                         │
│  • Table-level permissions                                      │
│  • Column-level access control                                  │
│  • Dynamic permission loading                                   │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Query Validation                                      │
│  • SQL syntax validation                                        │
│  • Schema compliance checking                                   │
│  • Injection prevention                                         │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Execution Security                                    │
│  • Parameterized queries                                        │
│  • Result filtering                                             │
│  • Error handling                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Permission Matrix Example

| Role | cust_mast | acct_mast | txn_hist | emp_mast | branch_mast |
|------|-----------|-----------|----------|----------|-------------|
| Teller | ALL | ALL | ALL | emp_id, emp_name | branch_id, branch_name |
| Manager | ALL | ALL | ALL | ALL | ALL |
| Auditor | ALL | ALL | ALL | ALL | ALL |
| IT | cust_id, cust_name | acct_id, cust_id | txn_id, acct_id | ALL | ALL |
| Customer Service | ALL | acct_id, cust_id, acct_type | txn_id, acct_id, amount | None | None |

## 🤖 AI Model Integration

### Model Selection Strategy

```python
def select_model(question_complexity, available_models):
    """
    Model selection based on query complexity and availability
    """
    if question_complexity == "simple":
        return "sqlcoder"  # Fast, accurate for simple queries
    elif question_complexity == "complex":
        return "mistral"   # Better reasoning for complex queries
    else:
        return "sqlcoder"  # Default fallback
```

### Prompt Engineering Strategy

#### SQLCoder Prompt Structure
```
1. Role Definition: "You are SQLCoder, an expert SQL generator"
2. Schema Context: "Schema: Table: X, Columns: Y, Z"
3. Rules: "ONLY use tables and columns listed below"
4. Question: "Question: {user_question}"
5. Output Format: "Generate ONLY the SQL query:"
```

#### Context Enhancement
- **Schema Context**: Exact table and column names
- **RAG Context**: Relevant schema descriptions
- **Data Dictionary**: Human-readable column descriptions
- **Relationship Hints**: Foreign key information

### Embedding Strategy

#### Schema Embedding Process
```python
# 1. Extract schema information
schema_data = pd.read_excel('data/data_dictionary.xlsx')

# 2. Create embedding texts
embedding_texts = []
for _, row in schema_data.iterrows():
    text = f"{row['Table']}.{row['Column']}: {row['Column Description']}"
    embedding_texts.append(text)

# 3. Generate embeddings
embeddings = model.encode(embedding_texts)

# 4. Store for retrieval
embeddings_df = pd.DataFrame({
    'text': embedding_texts,
    'embedding': embeddings.tolist()
})
```

#### Retrieval Process
```python
# 1. Encode user question
question_embedding = model.encode([question])

# 2. Find similar schema elements
similarities = cosine_similarity(question_embedding, embeddings)
top_indices = similarities.argsort()[0][-top_k:]

# 3. Return relevant context
context = [embedding_texts[i] for i in top_indices]
```

## 🔄 Error Handling & Resilience

### Error Handling Strategy

```python
def robust_query_processing(question, allowed_tables, allowed_columns):
    """
    Multi-layer error handling for query processing
    """
    try:
        # Layer 1: RAG-enhanced generation
        sql_query = generate_sql_with_rag(question, allowed_tables, allowed_columns)
        if validate_and_execute(sql_query):
            return sql_query, results
        
        # Layer 2: Fallback to direct generation
        sql_query = generate_sql_direct(question, allowed_tables, allowed_columns)
        if validate_and_execute(sql_query):
            return sql_query, results
        
        # Layer 3: Simple fallback query
        sql_query = generate_simple_query(allowed_tables[0])
        return sql_query, execute_simple_query(sql_query)
        
    except Exception as e:
        return None, f"Error: {str(e)}"
```

### Fallback Mechanisms

1. **Model Fallback**: SQLCoder → Mistral → Simple SQL
2. **Context Fallback**: RAG → Full Schema → Basic Schema
3. **Query Fallback**: Complex → Simple → Basic SELECT
4. **Execution Fallback**: Full Query → Limited Query → Sample Data

## 📈 Performance Optimization

### Caching Strategy

```python
@st.cache_data
def load_role_access():
    """Cache role access matrix"""
    return pd.read_excel('data/role_access.xlsx', index_col=0)

@st.cache_data
def load_data_dictionary():
    """Cache data dictionary"""
    return pd.read_excel('data/data_dictionary.xlsx')

@st.cache_resource
def load_embedding_model():
    """Cache embedding model"""
    return SentenceTransformer('all-MiniLM-L6-v2')
```

### Database Optimization

```sql
-- Indexes for performance
CREATE INDEX idx_cust_id ON acct_mast(cust_id);
CREATE INDEX idx_acct_id ON txn_hist(acct_id);
CREATE INDEX idx_branch_id ON acct_mast(branch_id);
CREATE INDEX idx_txn_date ON txn_hist(txn_date);
```

### LLM Optimization

```python
# Model configuration for optimal performance
llm_config = {
    'n_ctx': 2048,        # Context window
    'n_threads': 4,       # Parallel processing
    'n_batch': 512,       # Batch size
    'n_gpu_layers': 0     # CPU-only for compatibility
}
```

## 🔧 Configuration Management

### Environment Configuration

```python
# Configuration constants
DB_PATH = 'db/bank_exchange.db'
DATA_DICT_PATH = 'data/data_dictionary.xlsx'
ROLE_ACCESS_PATH = 'data/role_access.xlsx'
MODELS_DIR = 'models/'
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
```

### Dynamic Configuration Loading

```python
def load_config():
    """Load all configuration files"""
    config = {
        'database': load_database_config(),
        'models': load_model_config(),
        'roles': load_role_config(),
        'schema': load_schema_config()
    }
    return config
```

## 🧪 Testing Strategy

### Unit Testing

```python
def test_sql_generation():
    """Test SQL generation with known inputs"""
    question = "Show all customers"
    expected_sql = "SELECT * FROM cust_mast;"
    
    sql = generate_sql_llm(question, ['cust_mast'], {'cust_mast': ['cust_id', 'cust_name']})
    assert sql.strip().lower() == expected_sql.lower()
```

### Integration Testing

```python
def test_end_to_end_query():
    """Test complete query processing pipeline"""
    question = "Find customers with balance over 50000"
    
    # Test full pipeline
    sql, response, df = query_agent.answer_query(question, allowed_tables, allowed_columns)
    
    assert sql is not None
    assert response is not None
    assert df is not None
    assert len(df) >= 0
```

### Performance Testing

```python
def test_query_performance():
    """Test query response times"""
    start_time = time.time()
    
    # Execute query
    sql, response, df = query_agent.answer_query(test_question, allowed_tables, allowed_columns)
    
    end_time = time.time()
    response_time = end_time - start_time
    
    assert response_time < 5.0  # Should complete within 5 seconds
```

## 📊 Monitoring & Logging

### Query Logging

```python
def log_query(role, question, sql, response_time, success):
    """Log all queries for monitoring"""
    log_entry = {
        'timestamp': datetime.now(),
        'role': role,
        'question': question,
        'sql': sql,
        'response_time': response_time,
        'success': success
    }
    
    # Store in database or file
    query_logs.append(log_entry)
```

### Performance Metrics

```python
def collect_metrics():
    """Collect system performance metrics"""
    metrics = {
        'avg_response_time': calculate_avg_response_time(),
        'success_rate': calculate_success_rate(),
        'model_usage': get_model_usage_stats(),
        'popular_queries': get_popular_queries(),
        'error_rate': calculate_error_rate()
    }
    return metrics
```

## 🔮 Future Architecture Enhancements

### Planned Improvements

1. **Microservices Architecture**
   - Separate services for authentication, query processing, LLM integration
   - API gateway for unified access
   - Service discovery and load balancing

2. **Advanced RAG**
   - Multi-modal embeddings (text + schema structure)
   - Dynamic context window sizing
   - Query-specific context optimization

3. **Real-time Processing**
   - WebSocket connections for real-time updates
   - Streaming query results
   - Live data synchronization

4. **Advanced Security**
   - JWT token authentication
   - API rate limiting
   - Advanced audit logging
   - Data encryption at rest

5. **Scalability Improvements**
   - Database connection pooling
   - Model serving optimization
   - Horizontal scaling support
   - Cloud deployment ready

---

This technical overview provides a comprehensive understanding of the system's architecture, data flow, and component interactions. The modular design allows for easy maintenance, testing, and future enhancements while maintaining security and performance standards. 