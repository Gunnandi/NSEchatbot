# DataMuse (Advanced Role-Based RAG SQL Chatbot)

A sophisticated, offline-capable SQL chatbot system with role-based access control, dynamic schema loading, and open-source LLM integration.  
**Built with Streamlit, SQLite, and SQLCoder.**  
**The system is fully dynamic and schema-driven, with no hardcoded table or column logic, and can be used with any real database and schema.**

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Query Agent   │    │   LLM Interface │
│ (enhanced_app)  │◄──►│ (enhanced_query)│◄──►│ (enhanced_llm)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Role Access   │    │  Schema Embedder│    │   Local LLM     │
│ (Excel File)    │    │ (enhanced_embed)│    │ (SQLCoder/Ollama)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │    │  Data Dictionary│
│ (bank_exchange) │    │   (Excel File)  │
└─────────────────┘    └─────────────────┘
```

---

## 📁 Project Structure

```
cursor app/
├── create_bank_exchange_db.py      # Creates synthetic banking database
├── create_data_dictionary.py       # Generates Excel data dictionary (REQUIRED)
├── create_er_diagram.py            # (Optional) ER diagram visualization
├── create_schema_pdf.py            # (Optional) PDF schema documentation
├── create_role_access.py           # Generates role-based access matrix (REQUIRED)
│
├── enhanced_app.py                 # Main Streamlit application
├── enhanced_query_agent.py         # Query processing and validation
├── enhanced_llm_interface.py       # LLM integration (SQLCoder)
├── enhanced_embedding.py           # RAG with schema embeddings
│
├── db/
│   └── bank_exchange.db            # SQLite database
├── data/
│   ├── data_dictionary.xlsx        # Schema documentation (REQUIRED)
│   ├── role_access.xlsx            # Role permissions matrix (REQUIRED)
│   ├── schema.pdf                  # (Optional) Schema documentation
│   └── er_diagram.jpeg             # (Optional) Entity relationship diagram
│
├── models/
│   ├── sqlcoder (via Ollama)       # SQL generation model (REQUIRED)
│   └── mpnet-embedding/            # Embedding model for RAG
│
├── utils/
│   └── utils_auth.py               # Authentication utilities
│
└── README.md                       # This file
```

---

## 🔧 Key Features

- [x] **Offline-capable, open-source LLM (SQLCoder)**
- [x] **Role-based access control (dynamic, from Excel)**
- [x] **Dynamic schema loading (no hardcoding)**
- [x] **RAG-enhanced query generation (embeddings)**
- [x] **SQL validation and security**
- [x] **Natural language responses**
- [x] **Real-time query processing**
- [x] **Results visualization and download**
- [x] **Error handling and troubleshooting**
- [x] **Works with any real database/schema**

---

## 🚀 How It Works

1. **User logs in and selects a role** (Teller, Manager, Auditor, IT, Customer Service, etc.).
2. **System loads allowed tables/columns** for that role from `role_access.xlsx`.
3. **User asks a question in natural language.**
4. **RAG retrieves relevant schema context** from `data_dictionary.xlsx` using embeddings.
5. **SQLCoder generates SQL** using only the allowed schema and RAG context.
6. **SQL is validated and executed** against the database.
7. **Results are displayed** with options for charts and downloads.

---

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8+
- 8GB+ RAM (for LLM models)
- Windows/Linux/macOS

### Installation

```bash
# 1. Clone repository
cd <project-directory>

# 2. Create virtual environment
python -m venv venv
# Activate:
#   venv\Scripts\activate   # Windows
#   source venv/bin/activate # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama and SQLCoder model
#   - Download Ollama from https://ollama.ai/
#   - Start Ollama: ollama serve
#   - Install SQLCoder: ollama pull sqlcoder

# 5. Place required files:
#   - Ensure data_dictionary.xlsx and role_access.xlsx are in data/
```

### Database & Docs Setup

```bash
python create_bank_exchange_db.py         # Generate example database
python create_data_dictionary.py          # Generate data dictionary (Excel)
python create_role_access.py              # Generate role access matrix (Excel)
python create_er_diagram.py               # (Optional) ER diagram
python create_schema_pdf.py               # (Optional) PDF schema
```

### Ollama Setup

```bash
python setup_ollama.py                    # Automated Ollama setup
# OR manually:
# ollama serve                            # Start Ollama server
# ollama pull sqlcoder                    # Install SQLCoder model
```

### Running the Application

```bash
streamlit run enhanced_app.py
# Access at: http://localhost:8501
```

---

## 📊 Test Prompts

Try these in the chat UI (role-based results!):

- Show all customers.
- List accounts with balance over 50000.
- Find transactions from last month.
- Show total revenue by branch for last month.
- List employees who processed more than 100 transactions.
- Find customers who have both savings and checking accounts.

---

## 🐛 Troubleshooting

**Model not found:**  
- Run automated setup: `python setup_ollama.py`
- Or manually ensure Ollama is running: `ollama serve`
- Ensure SQLCoder model is installed: `ollama pull sqlcoder`
- Check installed models: `ollama list`

**Database errors:**  
- Regenerate with `python create_bank_exchange_db.py`.
- Ensure `db/` directory exists and is writable.

**Excel file errors:**  
- Ensure `data_dictionary.xlsx` and `role_access.xlsx` are present in `data/`.
- Only these two Excel files are required for schema/permissions.

**Memory issues:**  
- Use a smaller model or increase system RAM.

**LLM hallucinating schema:**  
- Check that the data dictionary and role access files are up to date and match the database.
- The system only uses the provided schema context; no hardcoded logic.

---

## 📚 Technical Details

- **All schema and permissions are loaded dynamically.**
- **No hardcoded table/column logic.**
- **Role-based RAG context for every query.**
- **Only SQLCoder is used for SQL generation.**
- **Easily extensible to any real database and schema.**

---

**Built with ❤️ for secure, efficient, and intelligent data querying**

---

