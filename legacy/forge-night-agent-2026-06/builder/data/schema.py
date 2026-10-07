"""
Phase 1: Builder Data Layer - DuckDB Schema and Session Management
"""

import duckdb
from datetime import datetime
import os

# Get the directory where this file is located (night_agent folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def init_schema():
    """Initialize the builder database schema."""
    
    # Ensure data directory exists - use workspace-relative path
    db_path = os.path.join(PROJECT_ROOT, "data", "builder.duckdb")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = duckdb.connect(db_path)
    
    # Create night_sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS night_sessions (
            session_date DATE PRIMARY KEY,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            phase_completed VARCHAR,
            concepts_found INTEGER,
            data JSON,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create roblox_projects table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roblox_projects (
            concept_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            genre VARCHAR,
            theme VARCHAR,
            core_mechanic VARCHAR,
            status VARCHAR DEFAULT 'concept',
            council_score DOUBLE DEFAULT 0.0,
            build_path VARCHAR DEFAULT '',
            nights_worked INTEGER DEFAULT 0,
            test_passed BOOLEAN DEFAULT FALSE,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.close()
    print("✓ Builder database schema initialized")

def get_connection():
    """Get a database connection."""
    db_path = os.path.join(PROJECT_ROOT, "data", "builder.duckdb")
    return duckdb.connect(db_path)

if __name__ == "__main__":
    init_schema()
