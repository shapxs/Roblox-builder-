"""
Phase 7: Night Agent Main Loop - Full autonomous operation from 8 PM to 6 AM
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Optional
import threading

# Import our components
from night_agent.session_manager import SessionManager, NightSession
from night_agent.roblox_researcher import RobloxResearcher, GameConcept
from night_agent.game_builder import GameBuilder, BuildResult
from night_agent.game_tester import GameTester, CouncilVerdict


class NightAgent:
    """Main autonomous agent that runs nightly from 8 PM to 6 AM."""
    
    TOP_GAMES_TO_BUILD = 2
    SESSION_END_HOUR = 6  # 6 AM ET
    
    def __init__(self):
        self.session_mgr = SessionManager()
        self.researcher = RobloxResearcher()
        self.builder = GameBuilder()
        self.tester = GameTester()
        
        # Progress tracking
        self.total_tasks = 0
        self.completed_tasks = 0
        self.start_time = None
        
        # Store concepts for quick lookup during build phase
        self.concepts_by_id: Dict[str, GameConcept] = {}
        
        # Load soul (agent identity) - use workspace directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.soul_path = os.path.join(script_dir, "..", "souls", "night_agent.md")
        self.soul = self._load_soul()
        
        print("Night Agent initialized")
        print(f"Identity: {self.soul[:100]}...")
    
    def _load_soul(self) -> str:
        """Load the agent identity file."""
        if os.path.exists(self.soul_path):
            with open(self.soul_path, "r") as f:
                return f.read()
        return "# Night Agent\n\nAutonomous Roblox game builder."
    
    def run(self):
        """Run the night agent loop."""
        print("\n" + "="*60)
        print("NIGHT AGENT STARTED")
        print("="*60)
        
        # Start session
        session = self.session_mgr.start_session()
        print(f"\nSession started: {session.session_date}")
        print(f"Start time: {session.start_time}")
        
        try:
            # Determine if we need research or can resume
            if session.phase_completed == "none":
                # Fresh start - run research
                session = self._run_research_phase(session)
            
            # Build and test games
            session = self._run_build_phase(session)
            
            # End session
            summary = self._create_session_summary(session)
            self.session_mgr.end_session(session, summary)
            
            print(f"\n{'='*60}")
            print("NIGHT AGENT COMPLETED")
            print("="*60)
            print(summary)
            
        except Exception as e:
            print(f"Error during night agent run: {str(e)}")
            session.errors.append(str(e))
            summary = f"Error: {str(e)}"
            self.session_mgr.end_session(session, summary)
    
    def _run_research_phase(self, session: NightSession) -> NightSession:
        """Run the research phase."""
        print("\n" + "="*60)
        print("RESEARCH PHASE")
        print("="*60)
        
        # Run research (this would take ~30 minutes in production)
        print("Starting market research...")
        print(f"Using {len(self.researcher.GAMING_PERSONAS)} personas and {len(self.researcher.RESEARCH_SOURCES)} sources")
        
        # For testing, we'll simulate quick research
        concepts = self._simulate_research()
        
        session.concepts_found = len(concepts)
        session.phase_completed = "research_complete"
        
        print(f"\n✓ Research complete. Found {len(concepts)} concepts.")
        
        # Select top games to build
        selected_concepts = concepts[:self.TOP_GAMES_TO_BUILD]
        
        self.total_tasks = len(selected_concepts) * 2  # Build + Test for each game
        
        # Store concept data in session for quick lookup
        for concept in selected_concepts:
            self.concepts_by_id[concept.concept_id] = concept
            
            session.games_in_progress.append(concept.concept_id)
            
            # Save project to database
            self.session_mgr.save_project({
                "concept_id": concept.concept_id,
                "name": concept.name,
                "genre": concept.genre,
                "theme": concept.theme,
                "core_mechanic": concept.core_mechanic,
                "status": "building"
            })
        
        print(f"✓ Selected {len(selected_concepts)} games to build:")
        for concept in selected_concepts:
            print(f"  - {concept.name}")
        
        return session
    
    def _simulate_research(self) -> List[GameConcept]:
        """Simulate research for testing purposes."""
        import uuid
        
        concepts = [
            GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre="tycoon",
                name="Mega Tycoon Empire",
                theme="neon_city",
                core_mechanic="Build and expand your business empire across multiple industries",
                hook="Real-time market fluctuations affect your profits",
                monetization=["VIP Pass ($499)", "Business Pack ($199)"],
                target_age="10-16",
                competition_level="MEDIUM",
                viral_potential="HIGH"
            ),
            GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre="simulator",
                name="Life Simulator Pro",
                theme="modern_city",
                core_mechanic="Experience different careers and life paths in a virtual world",
                hook="Dynamic relationships affect your career progression",
                monetization=["Career Pack ($149)", "Premium Lifestyle ($299)"],
                target_age="12-18",
                competition_level="LOW",
                viral_potential="MEDIUM"
            ),
            GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre="obby",
                name="Infinite Obby World",
                theme="fantasy_castle",
                core_mechanic="Navigate challenging obstacle courses and compete for high scores",
                hook="User-generated course creation system",
                monetization=["Course Creator Pack ($99)", "Premium Skins ($249)"],
                target_age="8-14",
                competition_level="HIGH",
                viral_potential="HIGH"
            ),
            GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre="roleplay",
                name="City Life RP",
                theme="urban_metropolis",
                core_mechanic="Live various lives in a bustling city with other players",
                hook="Realistic economy and job system",
                monetization=["Job Training Pass ($79)", "Luxury Apartment ($399)"],
                target_age="14-18",
                competition_level="MEDIUM",
                viral_potential="HIGH"
            ),
            GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre="survival",
                name="Last Stand Survival",
                theme="post_apocalyptic",
                core_mechanic="Survive against zombies and other players in a harsh world",
                hook="Dynamic weather and day/night cycles",
                monetization=["Survivor Pack ($129)", "Weapon Crate ($89)"],
                target_age="13-17",
                competition_level="HIGH",
                viral_potential="MEDIUM"
            )
        ]
        
        return concepts
    
    def _print_progress(self, current: int, total: int, task_name: str):
        """Print a progress bar with ETA."""
        if self.start_time is None:
            self.start_time = datetime.now()
        
        # Calculate progress
        percentage = (current / total) * 100
        
        # Calculate ETA
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if current > 0:
            time_per_task = elapsed / current
            remaining = (total - current) * time_per_task
            eta_minutes = int(remaining / 60)
            eta_seconds = int(remaining % 60)
            eta_str = f"{eta_minutes}m {eta_seconds}s"
        else:
            eta_str = "calculating..."
        
        # Print progress bar
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = chr(9632) * filled + chr(9617) * (bar_length - filled)
        
        print(f"\r[{task_name}] {bar} {percentage:.1f}% | ETA: {eta_str}", end="", flush=True)
    
    def _run_build_phase(self, session: NightSession) -> NightSession:
        """Run the build and test phase."""
        print("\n" + "="*60)
        print("BUILD PHASE")
        print("="*60)
        
        # Get current time
        start_time = datetime.now()
        self.start_time = start_time
        
        while True:
            # Check if we've reached 6 AM
            current_hour = datetime.now().hour
            if current_hour == self.SESSION_END_HOUR and datetime.now().minute >= 0:
                print(f"\nReached {self.SESSION_END_HOUR}:00 AM - stopping build phase")
                break
            
            # Process games in progress
            for concept_id in list(session.games_in_progress):
                # Check time limit (3 hours max per game)
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 10800:  # 3 hours
                    print(f"Time limit reached for {concept_id}")
                    break
                
                # Find the concept
                concept = self._find_concept_by_id(concept_id)
                if not concept:
                    continue
                
                print(f"\n{'='*60}")
                print(f"BUILDING: {concept.name}")
                print("="*60)
                
                try:
                    # Build the game with progress tracking
                    build_result = self.builder.build(concept)
                    
                    # Test the game with progress tracking
                    verdict = self.tester.test_game(concept, build_result.build_path)
                    
                    if verdict.is_ready:
                        print(f"\n🎉 GAME READY: {verdict.game_name}")
                        print(f"   Council Score: {verdict.overall_score}/10")
                        
                        # Update session
                        session.games_in_progress.remove(concept_id)
                        session.games_ready.append(concept_id)
                        
                        # Update database
                        self.session_mgr.save_project({
                            "concept_id": concept.concept_id,
                            "name": concept.name,
                            "status": "ready",
                            "council_score": verdict.overall_score,
                            "build_path": build_result.build_path,
                            "nights_worked": 1
                        })
                        
                    else:
                        print(f"\n⚠️  Game needs improvement: {verdict.game_name}")
                        print(f"   Score: {verdict.overall_score}/10")
                        print("   Improvements:")
                        for imp in verdict.improvements:
                            print(f"     - {imp}")
                        
                        # Update database with improvements
                        self.session_mgr.save_project({
                            "concept_id": concept.concept_id,
                            "name": concept.name,
                            "status": "needs_improvement",
                            "council_score": verdict.overall_score,
                            "build_path": build_result.build_path,
                            "notes": "; ".join(verdict.improvements),
                            "nights_worked": 1
                        })
                        
                except Exception as e:
                    print(f"Error building {concept.name}: {str(e)}")
                    session.errors.append(str(e))
            
            # Check if all games are done or ready
            if not session.games_in_progress:
                print("\nAll games processed!")
                break
            
            # Small delay to prevent infinite loop in testing
            time.sleep(1)
        
        return session
    
    def _find_concept_by_id(self, concept_id: str) -> Optional[GameConcept]:
        """Find a concept by its ID."""
        # First check if we have it in the agent's concepts
        if concept_id in self.concepts_by_id:
            return self.concepts_by_id[concept_id]
        
        return None
    
    def _create_session_summary(self, session: NightSession) -> str:
        """Create a summary of the night\'s work."""
        
        summary = f"""
NIGHT AGENT SESSION SUMMARY
===========================
Date: {session.session_date}
Start Time: {session.start_time}
End Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Research Results:
- Concepts Found: {session.concepts_found}
- Games in Progress: {len(session.games_in_progress)}
- Games Ready: {len(session.games_ready)}

Games Completed:
"""
        
        for concept_id in session.games_ready:
            concept = self._find_concept_by_id(concept_id)
            if concept:
                summary += f"- {concept.name} (READY)\n"
        
        if session.errors:
            summary += "\nErrors Encountered:\n"
            for error in session.errors:
                summary += f"- {error}\n"
        
        return summary


# For testing
if __name__ == "__main__":
    print("Testing Night Agent...")
    
    agent = NightAgent()
    
    # Verify all components initialize without errors
    print(f"Session manager: {type(agent.session_mgr).__name__}")
    print(f"Researcher: {type(agent.researcher).__name__}")
    print(f"Builder: {type(agent.builder).__name__}")
    print(f"Tester: {type(agent.tester).__name__}")
    print(f"Soul loaded: {len(agent.soul) > 100}")
    
    # Uncomment to run full night agent (takes hours)
    # agent.run()
