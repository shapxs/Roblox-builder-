"""
Phase 3: Session Manager - Multi-night state persistence
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

from data.schema import get_connection


@dataclass
class NightSession:
    """Represents a night agent session."""
    session_date: str
    start_time: str
    end_time: str = ""
    phase_completed: str = "none"
    concepts_found: int = 0
    games_in_progress: List[str] = field(default_factory=list)
    games_ready: List[str] = field(default_factory=list)
    summary: str = ""
    errors: List[str] = field(default_factory=list)
    concepts_data: Dict[str, dict] = field(default_factory=dict)  # Store concept data for quick lookup


class SessionManager:
    """Manages multi-night state persistence for the builder."""
    
    def __init__(self):
        # Get project root from script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, "..", "data", "builder.duckdb")
        
    def start_session(self) -> NightSession:
        """Start a new session or resume an unfinished one."""
        conn = get_connection()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check for existing incomplete session
        result = conn.execute(
            """
            SELECT * FROM night_sessions 
            WHERE session_date = ? AND phase_completed != 'complete'
            """,
            [today]
        ).fetchone()
        
        if result:
            # Resume existing session
            columns = ['session_date', 'start_time', 'end_time', 'phase_completed',
                      'concepts_found', 'data', 'summary']
            session_data = dict(zip(columns, result))
            
            session = NightSession(
                session_date=session_data['session_date'],
                start_time=session_data['start_time'],
                end_time=session_data['end_time'] or "",
                phase_completed=session_data['phase_completed'] or "none",
                concepts_found=session_data['concepts_found'] or 0,
                summary=session_data['summary'] or ""
            )
            
            # Load games from session data
            if session_data.get('data'):
                try:
                    data = json.loads(session_data['data'])
                    session.games_in_progress = data.get('games_in_progress', [])
                    session.games_ready = data.get('games_ready', [])
                except json.JSONDecodeError:
                    pass
            
            conn.close()
            return session
        
        # Create new session
        now = datetime.now().isoformat()
        
        # Insert new session record
        conn.execute("""
            INSERT INTO night_sessions 
            (session_date, start_time, phase_completed)
            VALUES (?, ?, 'none')
        """, [today, now])
        
        conn.close()
        
        return NightSession(
            session_date=today,
            start_time=now,
            phase_completed="none"
        )
    
    def save_project(self, project: dict):
        """Upsert a project to the database."""
        conn = get_connection()
        
        # Check if project exists
        existing = conn.execute(
            "SELECT concept_id FROM roblox_projects WHERE concept_id = ?",
            [project['concept_id']]
        ).fetchone()
        
        now = datetime.now().isoformat()
        
        if existing:
            # Update existing
            conn.execute("""
                UPDATE roblox_projects 
                SET name = ?, genre = ?, theme = ?, core_mechanic = ?,
                    status = ?, council_score = ?, build_path = ?,
                    nights_worked = nights_worked + 1, updated_at = ?
                WHERE concept_id = ?
            """, [
                project.get('name', ''),
                project.get('genre', ''),
                project.get('theme', ''),
                project.get('core_mechanic', ''),
                project.get('status', 'concept'),
                project.get('council_score', 0.0),
                project.get('build_path', ''),
                now,
                project['concept_id']
            ])
        else:
            # Insert new
            conn.execute("""
                INSERT INTO roblox_projects 
                (concept_id, name, genre, theme, core_mechanic, status,
                 council_score, build_path, nights_worked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                project['concept_id'],
                project.get('name', ''),
                project.get('genre', ''),
                project.get('theme', ''),
                project.get('core_mechanic', ''),
                project.get('status', 'concept'),
                project.get('council_score', 0.0),
                project.get('build_path', ''),
                project.get('nights_worked', 1)
            ])
        
        conn.close()
    
    def end_session(self, session: NightSession, summary: str):
        """End a session and save the summary."""
        conn = get_connection()
        
        # Update session record
        data = {
            'games_in_progress': session.games_in_progress,
            'games_ready': session.games_ready
        }
        
        conn.execute("""
            UPDATE night_sessions 
            SET end_time = ?, phase_completed = ?, concepts_found = ?,
                data = ?, summary = ?
            WHERE session_date = ?
        """, [
            datetime.now().isoformat(),
            "complete",
            session.concepts_found,
            json.dumps(data),
            summary,
            session.session_date
        ])
        
        conn.close()
    
    def get_all_projects(self) -> List[dict]:
        """Get all projects from the database."""
        conn = get_connection()
        
        result = conn.execute("""
            SELECT concept_id, name, genre, theme, core_mechanic,
                   status, council_score, build_path, nights_worked,
                   test_passed, notes, created_at
            FROM roblox_projects
            ORDER BY council_score DESC
        """).fetchall()
        
        columns = ['concept_id', 'name', 'genre', 'theme', 'core_mechanic',
                  'status', 'council_score', 'build_path', 'nights_worked',
                  'test_passed', 'notes', 'created_at']
        
        projects = [dict(zip(columns, row)) for row in result]
        conn.close()
        
        return projects
