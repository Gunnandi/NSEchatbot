# DataMuse (Advanced Role-Based RAG SQL Chatbot)

A robust, MySQL-only SQL chatbot system with role-based access control, dynamic schema and data row RAG, and open-source LLM integration.  
**Built with Streamlit, MySQL, and SQLCoder.**  
**The system is fully dynamic and schema-driven, with no hardcoded table or column logic, and can be used with any real MySQL database and schema.**

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
│ (MySQL Table)   │    │ (enhanced_embed)│    │ (SQLCoder/Ollama)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   MySQL DB      │    │  Data Dictionary│
│ (bankexchange)  │    │   (MySQL Table) │
└─────────────────┘    └─────────────────┘
```

---

## 📁 Project Structure

```
project_root/
├── create_bank_exchange_db.py      # Loads Excel data into MySQL (optional)
├── create_data_dictionary.py       # Generates data dictionary from MySQL (REQUIRED)
├── create_er_diagram.py            # (Optional) ER diagram visualization
├── create_schema_pdf.py            # (Optional) PDF schema documentation
├── create_role_access.py           # Generates role-based access matrix (REQUIRED)
│
├── enhanced_app.py                 # Main Streamlit application
├── enhanced_query_agent.py         # Query processing and validation
├── enhanced_llm_interface.py       # LLM integration (SQLCoder)
├── enhanced_embedding.py           # RAG with schema and data row embeddings
│
├── data/
│   ├── data_dictionary.xlsx        # Schema documentation (REQUIRED)
│   ├── role_access.xlsx            # Role permissions matrix (REQUIRED)
│   ├── schema.pdf                  # (Optional) Schema documentation
│   └── er_diagram.jpeg             # (Optional) Entity relationship diagram
│
├── models/
│   └── mpnet-embedding/            # Embedding model for RAG (auto-downloaded)
│
├── logs/
│   └── {username}.log              # Per-user logs of prompts and SQL queries
│
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

---

## 🔧 Key Features

- [x] **MySQL-only, no SQLite**
- [x] **Role-based access control (dynamic, from MySQL/Excel)**
- [x] **Dynamic schema and data row RAG (semantic search)**
- [x] **Per-user logging of prompts and SQL queries**
- [x] **No SQL shown in UI (for security)**
- [x] **Pie, bar, and line chart support for results**
- [x] **Offline-capable, open-source LLM (SQLCoder via Ollama)**
- [x] **Natural language responses**
- [x] **Real-time query processing**
- [x] **Results visualization and download**
- [x] **Error handling and troubleshooting**
- [x] **Works with any real MySQL database/schema**

---

## 🚀 How It Works

1. **User logs in with a role** (Teller, Manager, Auditor, IT, Customer Service, etc.).
2. **System loads allowed tables/columns** for that role from `role_access.xlsx`/MySQL.
3. **User asks a question in natural language.**
4. **RAG retrieves relevant schema and data row context** from MySQL using embeddings.
5. **SQLCoder generates SQL** using only the allowed schema and RAG context.
6. **SQL is validated and executed** against the MySQL database.
7. **Results are displayed** with options for pie, bar, and line charts, and CSV download.
8. **User prompt and generated SQL are logged** to `logs/{username}.log`.

---

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8+
- MySQL Server (with your schema/data)
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

# 5. Set up MySQL database and schema
#   - Use your own schema/data, or run create_bank_exchange_db.py if using Excel sources
#   - Run create_data_dictionary.py and create_role_access.py to generate required Excel files
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
- Run automated setup: `ollama serve` and `ollama pull sqlcoder`
- Ensure SQLCoder model is installed and Ollama is running

**Database errors:**  
- Ensure MySQL server is running and accessible
- Ensure your schema/data is loaded

**Excel file errors:**  
- Ensure `data_dictionary.xlsx` and `role_access.xlsx` are present in `data/`
- Only these two Excel files are required for schema/permissions

**Log file not created:**  
- Ensure the app has write permissions to the project directory
- Check the `logs/` directory for per-user log files

**Memory issues:**  
- Use a smaller model or increase system RAM

**LLM hallucinating schema:**  
- Check that the data dictionary and role access files are up to date and match the database
- The system only uses the provided schema context; no hardcoded logic

---

## 📚 Technical Details

- **All schema and permissions are loaded dynamically from MySQL.**
- **No hardcoded table/column logic.**
- **Role-based RAG context for every query, including real data row examples.**
- **Only SQLCoder is used for SQL generation.**
- **Easily extensible to any real MySQL database and schema.**
- **Per-user logs of all prompts and generated SQL queries.**
- **No SQL is shown in the UI for security.**
- **Pie, bar, and line chart support for results.**

---

**Built with ❤️ for secure, efficient, and intelligent data querying**

---


