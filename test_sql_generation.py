#!/usr/bin/env python3
"""
Test script for SQL generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_llm_interface import generate_sql_llm, clean_sql_response, validate_sql_syntax, generate_simple_sql

def test_sql_generation():
    """Test SQL generation with sample data"""
    
    # Sample test data
    allowed_tables = ['acct_mast']
    allowed_columns = {
        'acct_mast': ['acct_id', 'cust_id', 'acct_type', 'balance', 'branch_id', 'open_date']
    }
    
    # Sample questions to test
    test_questions = [
        "Show average balance by account type",
        "Count total accounts",
        "Show all accounts with balance over 50000",
        "List account types and their average balance"
    ]
    
    print("🧪 Testing SQL Generation")
    print("=" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Question: {question}")
        
        try:
            # Test LLM generation (this will fail if Ollama is not running)
            sql = generate_sql_llm(question, allowed_tables, allowed_columns, None)
            
            if sql:
                print(f"   Generated SQL: {sql}")
                
                # Test validation
                is_valid, msg = validate_sql_syntax(sql)
                print(f"   Validation: {'✅' if is_valid else '❌'} {msg}")
            else:
                print("   ❌ No SQL generated")
                
        except Exception as e:
            print(f"   ❌ LLM Error: {e}")
            print("   🔄 Testing fallback generation...")
            
            # Test fallback generation
            try:
                fallback_sql = generate_simple_sql(question, allowed_tables, allowed_columns)
                if fallback_sql:
                    print(f"   Fallback SQL: {fallback_sql}")
                    
                    # Test validation
                    is_valid, msg = validate_sql_syntax(fallback_sql)
                    print(f"   Validation: {'✅' if is_valid else '❌'} {msg}")
                else:
                    print("   ❌ No fallback SQL generated")
            except Exception as fallback_error:
                print(f"   ❌ Fallback Error: {fallback_error}")

def test_sql_cleaning():
    """Test SQL response cleaning"""
    
    print("\n🧹 Testing SQL Response Cleaning")
    print("=" * 50)
    
    test_cases = [
        # Test case 1: Markdown formatting
        ("```sql\nSELECT * FROM table;\n```", "SELECT * FROM table;"),
        
        # Test case 2: Extra text before and after
        ("Here's the query: SELECT * FROM table; This should be removed", "SELECT * FROM table;"),
        
        # Test case 3: No formatting
        ("SELECT * FROM table;", "SELECT * FROM table;"),
        
        # Test case 4: Missing semicolon
        ("SELECT * FROM table", "SELECT * FROM table;"),
        
        # Test case 5: Complex case
        ("```\nHere's the SQL:\nSELECT acct_type, AVG(balance) FROM acct_mast GROUP BY acct_type;\n```", 
         "SELECT acct_type, AVG(balance) FROM acct_mast GROUP BY acct_type;")
    ]
    
    for i, (input_sql, expected) in enumerate(test_cases, 1):
        cleaned = clean_sql_response(input_sql)
        status = "✅" if cleaned == expected else "❌"
        print(f"{i}. {status} Input: {repr(input_sql)}")
        print(f"   Output: {repr(cleaned)}")
        print(f"   Expected: {repr(expected)}")

def test_sql_validation():
    """Test SQL syntax validation"""
    
    print("\n🔍 Testing SQL Syntax Validation")
    print("=" * 50)
    
    test_cases = [
        # Valid SQL
        ("SELECT * FROM table;", True),
        ("SELECT acct_type, AVG(balance) FROM acct_mast GROUP BY acct_type;", True),
        ("SELECT COUNT(*) FROM table;", True),
        
        # Invalid SQL
        ("SELECT * FROM table", False),  # Missing semicolon (but this gets added)
        ("INVALID SQL", False),
        ("SELECT * FROM table WHERE column < value;", False),  # Invalid character
        ("SELECT * FROM table WHERE column > value;", False),  # Invalid character
    ]
    
    for i, (sql, should_be_valid) in enumerate(test_cases, 1):
        is_valid, msg = validate_sql_syntax(sql)
        status = "✅" if is_valid == should_be_valid else "❌"
        print(f"{i}. {status} SQL: {sql}")
        print(f"   Valid: {is_valid}, Expected: {should_be_valid}")
        print(f"   Message: {msg}")

if __name__ == "__main__":
    print("🚀 Starting SQL Generation Tests")
    print("=" * 60)
    
    test_sql_cleaning()
    test_sql_validation()
    test_sql_generation()
    
    print("\n🎉 Test completed!")
    print("\n💡 If you see LLM errors, make sure:")
    print("   1. Ollama is running: ollama serve")
    print("   2. SQLCoder model is installed: ollama pull sqlcoder")
    print("   3. Run: python setup_ollama.py") 