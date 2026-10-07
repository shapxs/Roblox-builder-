#!/usr/bin/env python3
"""
Forge Builder - Acceptance Test Suite

Run this to verify all phases are working correctly.
"""

import os
import sys
import tempfile
import uuid

# Add forge to path
sys.path.insert(0, os.path.expanduser("~/forge"))

from night_agent.session_manager import SessionManager
from night_agent.roblox_researcher import RobloxResearcher, GameConcept
from night_agent.game_builder import GameBuilder
from night_agent.game_tester import GameTester


def test_phase1_database():
    """Test Phase 1: Builder Data Layer"""
    print("\n" + "="*60)
    print("PHASE 1: Database Schema")
    print("="*60)
    
    from data.schema import init_schema, get_connection
    
    # Initialize schema
    init_schema()
    
    # Verify tables exist
    conn = get_connection()
    tables = [t[0] for t in conn.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchall()]
    
    assert 'night_sessions' in tables, "night_sessions table missing"
    assert 'roblox_projects' in tables, "roblox_projects table missing"
    
    conn.close()
    
    print("✓ Database schema initialized")
    print(f"✓ Tables: {tables}")
    return True


def test_phase3_session_manager():
    """Test Phase 3: Session Manager"""
    print("\n" + "="*60)
    print("PHASE 3: Session Manager")
    print("="*60)
    
    mgr = SessionManager()
    session = mgr.start_session()
    
    assert session.session_date, "Session date missing"
    assert session.start_time, "Start time missing"
    
    # Save a test project
    test_project = {
        'concept_id': str(uuid.uuid4())[:8],
        'name': 'Test Project',
        'genre': 'tycoon',
        'theme': 'space',
        'core_mechanic': 'Build and manage',
        'status': 'building'
    }
    mgr.save_project(test_project)
    
    # Get all projects
    projects = mgr.get_all_projects()
    assert len(projects) >= 1, "No projects saved"
    
    print(f"✓ Session started: {session.session_date}")
    print(f"✓ Projects in database: {len(projects)}")
    return True


def test_phase4_researcher():
    """Test Phase 4: Roblox Researcher"""
    print("\n" + "="*60)
    print("PHASE 4: Roblox Researcher (12 Sources)")
    print("="*60)
    
    researcher = RobloxResearcher()
    
    # Verify personas
    assert len(researcher.GAMING_PERSONAS) == 6, "Expected 6 personas"
    print(f"✓ Personas: {list(researcher.GAMING_PERSONAS.keys())}")
    
    # Verify sources (minimum 10)
    assert len(researcher.RESEARCH_SOURCES) >= 10, f"Expected at least 10 sources, got {len(researcher.RESEARCH_SOURCES)}"
    print(f"✓ Sources: {len(researcher.RESEARCH_SOURCES)}")
    
    # List all sources
    for source in researcher.RESEARCH_SOURCES:
        print(f"  - {source['name']}: {source['url']}")
    
    return True


def test_phase5_builder():
    """Test Phase 5: Game Builder"""
    print("\n" + "="*60)
    print("PHASE 5: Game Builder")
    print("="*60)
    
    # Create a test concept
    concept = GameConcept(
        concept_id=str(uuid.uuid4())[:8],
        genre='tycoon',
        name='Test Tycoon',
        theme='space',
        core_mechanic='Build and manage a space mining operation',
        hook='Real-time asteroid events',
        monetization=['VIP Pass', 'Starter Pack'],
        target_age='8-14',
        competition_level='LOW',
        viral_potential='MEDIUM'
    )
    
    builder = GameBuilder()
    
    # Build the game
    with tempfile.TemporaryDirectory() as tmpdir:
        project = builder.build(concept)
        
        assert project.concept_id == concept.concept_id, "Concept ID mismatch"
        assert os.path.exists(project.build_path), "Build path doesn't exist"
        assert project.scripts_generated >= 7, f"Expected at least 7 scripts, got {project.scripts_generated}"
        
        # Verify Lua files
        lua_files = []
        for root, dirs, files in os.walk(project.build_path):
            for f in files:
                if f.endswith('.lua'):
                    lua_files.append(f)
        
        print(f"✓ Game built at: {project.build_path}")
        print(f"✓ Lua scripts generated: {len(lua_files)}")
        
        # List the scripts
        for script in sorted(lua_files):
            print(f"  - {script}")
    
    return True


def test_phase6_tester():
    """Test Phase 6: Game Tester"""
    print("\n" + "="*60)
    print("PHASE 6: Game Tester")
    print("="*60)
    
    tester = GameTester()
    
    # Verify threshold
    assert tester.READY_THRESHOLD == 7.5, f"Expected threshold 7.5, got {tester.READY_THRESHOLD}"
    print(f"✓ Ready threshold: {tester.READY_THRESHOLD}")
    
    # Create a test concept and build
    concept = GameConcept(
        concept_id=str(uuid.uuid4())[:8],
        genre='tycoon',
        name='Test Game',
        theme='space',
        core_mechanic='Build and manage',
        hook='Unique mechanics',
        monetization=['VIP Pass'],
        target_age='8-14',
        competition_level='LOW',
        viral_potential='MEDIUM'
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create basic structure
        os.makedirs(os.path.join(tmpdir, "scripts", "ServerScriptService"))
        
        # Save test files
        with open(os.path.join(tmpdir, "game-design-document.md"), "w") as f:
            f.write("# Test Game\n\nThis is a test game.")
        
        verdict = tester.test_game(concept, tmpdir)
        
        assert verdict.concept_id == concept.concept_id, "Concept ID mismatch"
        assert verdict.game_name == concept.name, "Game name mismatch"
        assert 0 <= verdict.overall_score <= 10, f"Score out of range: {verdict.overall_score}"
        
        print(f"✓ Council score: {verdict.overall_score}/10")
        print(f"✓ Is ready: {verdict.is_ready}")
        
        if verdict.improvements:
            print("✓ Improvements suggested:")
            for imp in verdict.improvements:
                print(f"  - {imp}")
    
    return True


def main():
    """Run all acceptance tests."""
    print("="*60)
    print("FORGE BUILDER ACCEPTANCE TESTS")
    print("="*60)
    
    tests = [
        ("Phase 1: Database Schema", test_phase1_database),
        ("Phase 3: Session Manager", test_phase3_session_manager),
        ("Phase 4: Roblox Researcher", test_phase4_researcher),
        ("Phase 5: Game Builder", test_phase5_builder),
        ("Phase 6: Game Tester", test_phase6_tester),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            results.append((name, f"ERROR: {str(e)}"))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name}: {result}")
    
    passed = sum(1 for _, r in results if r == "PASS")
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
