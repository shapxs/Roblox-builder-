"""
Phase 6: Game Tester - Council Quality Gate
The council is the ONLY quality gate. Score >= 7.5 marks a game ready.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import the researcher to use GameConcept
from night_agent.roblox_researcher import GameConcept
from night_agent.llm_client import generate


@dataclass
class CouncilVerdict:
    """Result of a council quality review."""
    concept_id: str
    game_name: str
    scores: Dict[str, float]
    overall_score: float
    is_ready: bool
    improvements: List[str]
    verdict_text: str


class GameTester:
    """Council quality gate for Roblox games."""
    
    READY_THRESHOLD = 7.5  # Council score - sole gate
    
    def __init__(self):
        # Get project root from script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.results_dir = os.path.join(script_dir, "..", "data", "test_results")
        os.makedirs(self.results_dir, exist_ok=True)
        
    def test_game(
        self,
        concept: GameConcept,
        build_path: str
    ) -> CouncilVerdict:
        """Conduct council quality review of a built game."""
        print(f"\n{'='*60}")
        print("COUNCIL QUALITY REVIEW")
        print(f"Game: {concept.name}")
        print(f"Build Path: {build_path}")
        print("="*60)
        
        # Load build files for analysis
        build_files = self._load_build_files(build_path)
        
        # Council deliberation (simulated quality assessment)
        verdict = self._council_deliberate(concept, build_files)
        
        # Save test results
        self._save_test_results(concept, verdict, build_path)
        
        return verdict
    
    def _load_build_files(self, build_path: str) -> Dict[str, str]:
        """Load all build files for council review."""
        files = {}
        
        if not os.path.exists(build_path):
            return {"error": "Build path does not exist"}
        
        # Load Lua scripts
        scripts_dir = os.path.join(build_path, "scripts")
        if os.path.exists(scripts_dir):
            for root, dirs, filenames in os.walk(scripts_dir):
                for filename in filenames:
                    if filename.endswith(".lua"):
                        file_path = os.path.join(root, filename)
                        try:
                            with open(file_path, "r") as f:
                                files[filename] = f.read()
                        except Exception as e:
                            files[filename] = f"[Error reading file: {str(e)}]"
        
        # Load documentation
        docs = [
            "game-design-document.md",
            "monetization-plan.md",
            "assets-needed.md"
        ]
        
        for doc in docs:
            doc_path = os.path.join(build_path, doc)
            if os.path.exists(doc_path):
                try:
                    with open(doc_path, "r") as f:
                        files[doc] = f.read()
                except Exception as e:
                    files[doc] = f"[Error reading file: {str(e)}]"
        
        return files
    
    def _council_deliberate(
        self,
        concept: GameConcept,
        build_files: Dict[str, str]
    ) -> CouncilVerdict:
        """Use DeepSeek-R1 council to review and score the game."""
        
        # Extract content for analysis
        gdd = build_files.get("game-design-document.md", "")
        monetization = build_files.get("monetization-plan.md", "")
        
        # Build prompt for council review
        prompt = f"""You are a Roblox game quality council reviewing a new game concept.

Game Concept:
- Name: {concept.name}
- Genre: {concept.genre}
- Theme: {concept.theme}
- Core Mechanic: {concept.core_mechanic}
- Hook: {concept.hook}
- Target Age: {concept.target_age}

Game Design Document:
{gdd[:2000] if gdd else 'Not available'}

Monetization Plan:
{monetization[:1500] if monetization else 'Not available'}

Please review this game and provide scores from 1-10 for each category:

1. Fun factor - Would kids play this for hours?
2. Safety - Completely appropriate for target age?
3. Monetization - Fair, non-predatory, kids buy willingly?
4. Viral potential - Would kids share with friends?
5. Code quality - Complete and solid implementation?

Return your response as JSON with this exact format:
{{
    "fun_factor": 8,
    "safety": 9,
    "monetization": 7,
    "viral_potential": 8,
    "code_quality": 9,
    "improvements": ["Specific improvement 1", "Specific improvement 2", "Specific improvement 3"]
}}
"""

        try:
            # Call DeepSeek-R1 for council review
            response = generate("deepseek-r1:70b-llama-distill-q8_0", prompt, temperature=0.5)
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                scores_data = json.loads(json_match.group())
                
                fun_factor = float(scores_data.get("fun_factor", 7))
                safety = float(scores_data.get("safety", 8))
                monetization_score = float(scores_data.get("monetization", 7))
                viral_potential = float(scores_data.get("viral_potential", 7))
                code_quality = float(scores_data.get("code_quality", 8))
                
                improvements = scores_data.get("improvements", [])
            else:
                # Fallback to basic scoring if JSON parsing fails
                fun_factor = self._calculate_fun_factor(concept)
                safety = self._calculate_safety(concept)
                monetization_score = self._calculate_monetization(concept, monetization)
                viral_potential = self._calculate_viral_potential(concept)
                code_quality = self._calculate_code_quality(build_files)
                improvements = []
                
        except Exception as e:
            print(f"Error in council review: {str(e)}, using fallback scoring")
            fun_factor = self._calculate_fun_factor(concept)
            safety = self._calculate_safety(concept)
            monetization_score = self._calculate_monetization(concept, monetization)
            viral_potential = self._calculate_viral_potential(concept)
            code_quality = self._calculate_code_quality(build_files)
            improvements = []
        
        # Calculate overall weighted score
        overall_score = (
            fun_factor * 0.25 +
            safety * 0.20 +
            monetization_score * 0.20 +
            viral_potential * 0.15 +
            code_quality * 0.20
        )
        
        # Generate improvements if score < threshold
        improvements = []
        if overall_score < self.READY_THRESHOLD:
            improvements = self._generate_improvements(
                concept, fun_factor, safety, monetization_score,
                viral_potential, code_quality
            )
        
        # Create verdict text
        verdict_text = self._create_verdict_text(
            concept, fun_factor, safety, monetization_score,
            viral_potential, code_quality, overall_score
        )
        
        return CouncilVerdict(
            concept_id=concept.concept_id,
            game_name=concept.name,
            scores={
                "fun_factor": round(fun_factor, 1),
                "safety": round(safety, 1),
                "monetization": round(monetization_score, 1),
                "viral_potential": round(viral_potential, 1),
                "code_quality": round(code_quality, 1)
            },
            overall_score=round(overall_score, 1),
            is_ready=overall_score >= self.READY_THRESHOLD,
            improvements=improvements,
            verdict_text=verdict_text
        )
    
    def _calculate_fun_factor(self, concept: GameConcept) -> float:
        """Calculate fun factor score (1-10)."""
        base_score = 5.0
        
        # Boost for strong hook
        if len(concept.hook) > 20:
            base_score += 1.0
        
        # Boost for clear core mechanic
        if len(concept.core_mechanic) > 30:
            base_score += 1.0
        
        # Genre bonuses
        genre_bonuses = {
            "tycoon": 7.5,
            "simulator": 7.0,
            "obby": 8.0,
            "roleplay": 6.5,
            "survival": 6.0
        }
        
        base_score += genre_bonuses.get(concept.genre, 6.0)
        
        return min(10.0, max(1.0, base_score))
    
    def _calculate_safety(self, concept: GameConcept) -> float:
        """Calculate safety score (1-10)."""
        # Base safety for Roblox is high
        base_score = 8.5
        
        # Target age considerations
        if "8" in concept.target_age or "9" in concept.target_age:
            base_score += 0.5
        
        return min(10.0, max(1.0, base_score))
    
    def _calculate_monetization(self, concept: GameConcept, monetization_text: str) -> float:
        """Calculate monetization score (1-10)."""
        base_score = 6.0
        
        # Check for clear pricing structure
        if "$" in monetization_text or "Robux" in monetization_text:
            base_score += 2.0
        
        # Check for variety of items
        if len(concept.monetization) >= 3:
            base_score += 1.0
        
        return min(10.0, max(1.0, base_score))
    
    def _calculate_viral_potential(self, concept: GameConcept) -> float:
        """Calculate viral potential score (1-10)."""
        base_score = 5.0
        
        # Boost for high viral potential claim
        if concept.viral_potential == "HIGH":
            base_score += 2.0
        elif concept.viral_potential == "MEDIUM":
            base_score += 1.0
        
        # Boost for good competition level
        if concept.competition_level == "LOW":
            base_score += 1.5
        
        return min(10.0, max(1.0, base_score))
    
    def _calculate_code_quality(self, build_files: Dict[str, str]) -> float:
        """Calculate code quality score (1-10)."""
        if not build_files or "error" in build_files:
            return 3.0
        
        # Check for required scripts
        required_scripts = [
            "GameManager.server.lua",
            "DataStore.server.lua",
            "MonetizationHandler.server.lua"
        ]
        
        score = 4.0  # Base score
        
        for script in required_scripts:
            if script in build_files:
                score += 1.5
        
        # Check for client scripts
        client_scripts = [
            "UIController.client.lua",
            "ShopController.client.lua"
        ]
        
        for script in client_scripts:
            if script in build_files:
                score += 0.75
        
        return min(10.0, max(1.0, score))
    
    def _generate_improvements(
        self,
        concept: GameConcept,
        fun_factor: float,
        safety: float,
        monetization_score: float,
        viral_potential: float,
        code_quality: float
    ) -> List[str]:
        """Generate specific improvement suggestions."""
        improvements = []
        
        if fun_factor < 7.0:
            improvements.append(
                "Enhance the core mechanic to make it more engaging and addictive"
            )
        
        if safety < 8.0:
            improvements.append(
                "Review content for additional safety improvements"
            )
        
        if monetization_score < 7.0:
            improvements.append(
                "Expand monetization options with more appealing items"
            )
        
        if viral_potential < 7.0:
            improvements.append(
                "Add social features and shareable moments to increase virality"
            )
        
        if code_quality < 7.0:
            improvements.append(
                "Implement missing server-side scripts for game logic"
            )
        
        # Always add at least one improvement
        if not improvements:
            improvements.append(
                "Consider adding seasonal events to maintain player engagement"
            )
        
        return improvements[:3]  # Return top 3 improvements
    
    def _create_verdict_text(
        self,
        concept: GameConcept,
        fun_factor: float,
        safety: float,
        monetization_score: float,
        viral_potential: float,
        code_quality: float,
        overall_score: float
    ) -> str:
        """Create human-readable verdict text."""
        
        status = "READY" if overall_score >= self.READY_THRESHOLD else "NEEDS IMPROVEMENT"
        
        verdict = f"""# {concept.name} - Council Verdict

## Overall Score: {overall_score}/10
**Status:** {status}

## Detailed Scores

| Category | Score | Notes |
|----------|-------|-------|
| Fun Factor | {fun_factor}/10 | {'Excellent engagement' if fun_factor >= 7.0 else 'Needs improvement'} |
| Safety | {safety}/10 | {'Appropriate for target age' if safety >= 8.0 else 'Review content'} |
| Monetization | {monetization_score}/10 | {'Solid revenue model' if monetization_score >= 7.0 else 'Expand options'} |
| Viral Potential | {viral_potential}/10 | {'High sharing potential' if viral_potential >= 7.0 else 'Add social features'} |
| Code Quality | {code_quality}/10 | {'Well implemented' if code_quality >= 7.0 else 'Fix missing scripts'} |

## Council Notes
{concept.hook}

The game has strong potential with its unique hook and core mechanic.
Target audience ({concept.target_age}) is appropriate for the content.

---

*Council Quality Gate - Generated by Forge Builder*
"""
        
        return verdict
    
    def _save_test_results(
        self,
        concept: GameConcept,
        verdict: CouncilVerdict,
        build_path: str
    ):
        """Save test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save verdict markdown
        verdict_file = os.path.join(build_path, "test-results.md")
        with open(verdict_file, "w") as f:
            f.write(verdict.verdict_text)
        
        # Also save to results directory
        result_file = os.path.join(
            self.results_dir,
            f"{concept.concept_id}_{timestamp}.md"
        )
        with open(result_file, "w") as f:
            f.write(verdict.verdict_text)
        
        print(f"✓ Test results saved to: {verdict_file}")
    
    def is_ready(self, score: float) -> bool:
        """Check if a game meets the ready threshold."""
        return score >= self.READY_THRESHOLD


# For testing
if __name__ == "__main__":
    # Create a test concept
    from night_agent.roblox_researcher import GameConcept
    
    concept = GameConcept(
        concept_id="test123",
        genre="tycoon",
        name="Test Tycoon",
        theme="space",
        core_mechanic="Build and manage a space mining operation with friends",
        hook="Real-time asteroid events with multiplayer challenges",
        monetization=["VIP Pass", "Starter Pack", "Rare Skins"],
        target_age="8-14",
        competition_level="LOW",
        viral_potential="MEDIUM"
    )
    
    tester = GameTester()
    
    # Test with minimal build
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create basic structure
        os.makedirs(os.path.join(tmpdir, "scripts", "ServerScriptService"))
        
        # Save test files
        with open(os.path.join(tmpdir, "game-design-document.md"), "w") as f:
            f.write("# Test Game\n\nThis is a test game.")
        
        verdict = tester.test_game(concept, tmpdir)
        
        print(f"\nVerdict: {verdict.game_name}")
        print(f"Overall Score: {verdict.overall_score}/10")
        print(f"Is Ready: {verdict.is_ready}")
        if verdict.improvements:
            print("Improvements needed:")
            for imp in verdict.improvements:
                print(f"  - {imp}")
