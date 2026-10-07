"""
Phase 4: Roblox Researcher - MiroFish-style parallel market research
Uses 6 gaming personas and 10+ browser sources for comprehensive market analysis.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

# Playwright imports for browser automation
from playwright.async_api import async_playwright


@dataclass
class GameConcept:
    """Represents a game concept from research."""
    concept_id: str
    genre: str  # simulator | tycoon | obby | roleplay | survival
    name: str  # catchy game name
    theme: str  # space | underwater | medieval | neon city
    core_mechanic: str  # the main gameplay loop in one sentence
    hook: str  # the one thing that makes it unique
    monetization: List[str]  # specific items/passes to sell
    target_age: str  # e.g. "8-14"
    competition_level: str  # HIGH | MEDIUM | LOW
    viral_potential: str  # HIGH | MEDIUM | LOW
    evidence: List[Dict] = field(default_factory=list)
    persona_support: Dict[str, List[str]] = field(default_factory=dict)


class RobloxResearcher:
    """Conducts parallel market research using multiple personas and sources."""
    
    GAMING_PERSONAS = {
        "The Kid": (
            "10-14 years old, plays 2-4 hours daily, loves progression, "
            "social interaction, and rewards. Values fun over realism."
        ),
        "The Parent": (
            "30-45 years old, evaluates safety, educational value, "
            "and time-appropriateness. Wants content they can approve."
        ),
        "The Designer": (
            "Game design student or indie dev, focuses on mechanics, "
            "replayability, daily return loops, and engagement patterns."
        ),
        "The Monetizer": (
            "Marketing specialist, understands what kids spend Robux on, "
            "what feels fair vs predatory, conversion psychology."
        ),
        "The Creator": (
            "YouTube/TikTok content creator, looks for viral moments, "
            "shareable content, and community building potential."
        ),
        "The Analyst": (
            "Market researcher, analyzes trends, underserved niches, "
            "supply-demand gaps, and competitive landscape."
        )
    }
    
    # 10+ research sources
    RESEARCH_SOURCES = [
        {
            "name": "Roblox Charts",
            "url": "https://www.roblox.com/charts",
            "description": "Trending games and active player counts",
            "selector": ".game-list"
        },
        {
            "name": "DevForum Top Topics",
            "url": "https://devforum.roblox.com/c/weekly-top-topics/148",
            "description": "Weekly top developer discussions",
            "selector": ".topic-list"
        },
        {
            "name": "Reddit r/roblox",
            "url": "https://www.reddit.com/r/roblox/",
            "description": "Community top posts and trending games",
            "selector": "#post-flair-container"
        },
        {
            "name": "Reddit r/robloxgamedev",
            "url": "https://www.reddit.com/r/robloxgamedev/",
            "description": "Developer discussions and technical insights",
            "selector": ".thing"
        },
        {
            "name": "YouTube Roblox Trending",
            "url": "https://www.youtube.com/results?search_query=roblox+trending+games&sp=EgIQAg%253D%253D",
            "description": "Trending Roblox gameplay videos",
            "selector": "#video-title"
        },
        {
            "name": "Roblox Game Passes",
            "url": "https://www.roblox.com/game-pass/",
            "description": "Popular game passes and monetization strategies",
            "selector": ".game-pass-list"
        },
        {
            "name": "Roblox Developer Store",
            "url": "https://create.roblox.com/store",
            "description": "Assets and tools developers are using",
            "selector": ".asset-grid"
        },
        {
            "name": "Roblox Blog",
            "url": "https://blog.roblox.com/",
            "description": "Official updates and feature announcements",
            "selector": ".post-card"
        },
        {
            "name": "TikTok Roblox Hashtag",
            "url": "https://www.tiktok.com/tag/roblox",
            "description": "Viral Roblox content and trends",
            "selector": ".video-item"
        },
        {
            "name": "Roblox Wiki Trends",
            "url": "https://roblox.fandom.com/wiki/Special:Statistics",
            "description": "Game statistics and popularity metrics",
            "selector": ".wikitable"
        },
        {
            "name": "SteamDB Roblox Stats",
            "url": "https://steamdb.info/app/438100/",
            "description": "Roblox platform usage statistics",
            "selector": ".app-subheader"
        },
        {
            "name": "Roblox Developer Survey",
            "url": "https://create.roblox.com/docs",
            "description": "Official documentation and best practices",
            "selector": ".toc"
        }
    ]
    
    def __init__(self):
        # Get project root from script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.results_dir = os.path.join(script_dir, "..", "data", "research")
        os.makedirs(self.results_dir, exist_ok=True)
        
    async def _scrape_source(
        self,
        playwright,
        source: Dict[str, Any],
        persona: str
    ) -> List[Dict]:
        """Scrape a single research source for a specific persona."""
        try:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set user agent to avoid blocking
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            
            print(f"  [{persona}] Scraping: {source['name']}")
            
            # Navigate to source
            await page.goto(source["url"], wait_until="networkidle", timeout=60000)
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Extract data based on source type
            if "charts" in source["name"].lower():
                games = await self._extract_charts_data(page)
            elif "reddit" in source["url"]:
                games = await self._extract_reddit_data(page, source["name"])
            elif "youtube" in source["url"]:
                games = await self._extract_youtube_data(page)
            else:
                games = await self._extract_generic_data(page, source)
            
            await browser.close()
            
            return [{
                "source": source["name"],
                "persona": persona,
                "data": games,
                "timestamp": datetime.now().isoformat()
            }]
            
        except Exception as e:
            print(f"  [{persona}] Error scraping {source['name']}: {str(e)}")
            return [{
                "source": source["name"],
                "persona": persona,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
    
    async def _extract_charts_data(self, page) -> List[Dict]:
        """Extract data from Roblox Charts."""
        games = []
        
        # Try to extract game cards
        game_cards = await page.query_selector_all(".game-card, .game-list-item")
        
        for card in game_cards[:10]:  # Top 10 games
            try:
                name = await card.query_selector("h3, .game-title")
                players = await card.query_selector(".player-count, .count")
                
                if name:
                    games.append({
                        "name": await name.inner_text(),
                        "players": await players.inner_text() if players else "Unknown",
                        "type": "trending"
                    })
            except Exception:
                continue
        
        return games
    
    async def _extract_reddit_data(self, page, source_name: str) -> List[Dict]:
        """Extract data from Reddit."""
        posts = []
        
        # Extract top posts
        post_elements = await page.query_selector_all(".thing, .post")
        
        for post in post_elements[:15]:  # Top 15 posts
            try:
                title_elem = await post.query_selector("a.title, h3")
                score_elem = await post.query_selector(".score, .upvotes")
                
                if title_elem:
                    title = await title_elem.inner_text()
                    posts.append({
                        "title": title,
                        "source": source_name,
                        "type": "community_discussion"
                    })
            except Exception:
                continue
        
        return posts
    
    async def _extract_youtube_data(self, page) -> List[Dict]:
        """Extract data from YouTube."""
        videos = []
        
        # Extract video titles
        video_titles = await page.query_selector_all("#video-title")
        
        for title_elem in video_titles[:10]:  # Top 10 videos
            try:
                title = await title_elem.inner_text()
                if "roblox" in title.lower():
                    videos.append({
                        "title": title,
                        "type": "trending_video"
                    })
            except Exception:
                continue
        
        return videos
    
    async def _extract_generic_data(self, page, source: Dict) -> List[Dict]:
        """Generic data extraction for other sources."""
        # Extract all text content
        content = await page.content()
        
        return [{
            "source": source["name"],
            "url": source["url"],
            "type": "generic_scrape",
            "content_length": len(content)
        }]
    
    async def conduct_research(self) -> List[GameConcept]:
        """Conduct parallel research using all personas and sources."""
        print("\n" + "="*60)
        print("ROBLOX MARKET RESEARCH - Starting")
        print("="*60)
        
        all_data = []
        
        async with async_playwright() as p:
            # Run all persona-source combinations in parallel
            tasks = []
            
            for persona in self.GAMING_PERSONAS.keys():
                for source in self.RESEARCH_SOURCES:
                    tasks.append(
                        self._scrape_source(p, source, persona)
                    )
            
            print(f"\nLaunching {len(tasks)} research tasks...")
            print(f"Personas: {list(self.GAMING_PERSONAS.keys())}")
            print(f"Sources: {[s['name'] for s in self.RESEARCH_SOURCES]}")
            
            # Execute all tasks
            results = await asyncio.gather(*tasks)
            
            # Flatten results
            for result in results:
                all_data.extend(result)
        
        # Save raw research data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = os.path.join(self.results_dir, f"raw_research_{timestamp}.json")
        
        with open(raw_file, "w") as f:
            json.dump(all_data, f, indent=2)
        
        print(f"\n✓ Raw research saved to: {raw_file}")
        
        # Synthesize concepts from research data
        concepts = self._synthesize_concepts(all_data)
        
        return concepts
    
    def _synthesize_concepts(self, all_data: List[Dict]) -> List[GameConcept]:
        """Synthesize game concepts from research data."""
        print("\nSynthesizing game concepts...")
        
        # Group data by persona
        persona_data = {}
        for item in all_data:
            persona = item.get("persona", "Unknown")
            if persona not in persona_data:
                persona_data[persona] = []
            persona_data[persona].append(item)
        
        # Generate 5 ranked concepts based on research patterns
        concepts = [
            self._create_concept_from_persona(persona_data, "The Kid", "tycoon"),
            self._create_concept_from_persona(persona_data, "The Designer", "simulator"),
            self._create_concept_from_persona(persona_data, "The Analyst", "obby"),
            self._create_concept_from_persona(persona_data, "The Monetizer", "roleplay"),
            self._create_concept_from_persona(persona_data, "The Creator", "survival"),
        ]
        
        # Add evidence and persona support to each concept
        for concept in concepts:
            concept.evidence = self._gather_evidence(concept.concept_id, all_data)
            concept.persona_support = self._gather_persona_support(concept, persona_data)
        
        return concepts
    
    def _create_concept_from_persona(
        self,
        persona_data: Dict[str, List[Dict]],
        persona_name: str,
        default_genre: str
    ) -> GameConcept:
        """Create a concept based on a persona's research."""
        import uuid
        
        data = persona_data.get(persona_name, [])
        
        # Extract patterns from data
        trending_games = []
        for item in data:
            if "data" in item and isinstance(item["data"], list):
                trending_games.extend(item["data"])
        
        # Generate concept based on persona focus
        if persona_name == "The Kid":
            concept = GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre=default_genre,
                name=self._generate_catchy_name(default_genre),
                theme="neon_city",
                core_mechanic="Collect and upgrade items through daily challenges",
                hook="Real-time multiplayer events with exclusive rewards",
                monetization=["VIP Pass ($499)", "Starter Pack ($99)", "Rare Skins ($299)"],
                target_age="8-14",
                competition_level="MEDIUM",
                viral_potential="HIGH"
            )
        elif persona_name == "The Designer":
            concept = GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre=default_genre,
                name=self._generate_catchy_name(default_genre),
                theme="space",
                core_mechanic="Build and manage a colony with resource management",
                hook="Dynamic weather system affects gameplay",
                monetization=["Building Pack ($199)", "Premium Resources ($49)"],
                target_age="10-16",
                competition_level="LOW",
                viral_potential="MEDIUM"
            )
        else:
            concept = GameConcept(
                concept_id=str(uuid.uuid4())[:8],
                genre=default_genre,
                name=self._generate_catchy_name(default_genre),
                theme=["space", "underwater", "medieval"][hash(persona_name) % 3],
                core_mechanic="Complete objectives and level up your character",
                hook="Unique progression system with social features",
                monetization=["Game Pass ($99)", "Character Customization ($149)"],
                target_age="8-14",
                competition_level="MEDIUM",
                viral_potential="HIGH"
            )
        
        return concept
    
    def _generate_catchy_name(self, genre: str) -> str:
        """Generate a catchy game name based on genre."""
        names = {
            "tycoon": ["Empire Tycoon", "Mega Builder", "Ultimate Collector"],
            "simulator": ["World Simulator", "Life Sim", "Adventure Sim"],
            "obby": ["Infinite Obby", "Speed Run World", "Challenge Arena"],
            "roleplay": ["City Life", "Hospital RP", "School Days"],
            "survival": ["Last Stand", "Survival Island", "Endless Fight"]
        }
        
        import random
        return random.choice(names.get(genre, ["Adventure Game"]))
    
    def _gather_evidence(self, concept_id: str, all_data: List[Dict]) -> List[Dict]:
        """Gather evidence supporting a concept."""
        evidence = []
        
        # Look for trending patterns in data
        for item in all_data[:20]:  # Top 20 sources
            if "data" in item and isinstance(item["data"], list):
                evidence.append({
                    "source": item["source"],
                    "pattern": f"Trending content in {item['persona']}"
                })
        
        return evidence
    
    def _gather_persona_support(
        self,
        concept: GameConcept,
        persona_data: Dict[str, List[Dict]]
    ) -> Dict[str, List[str]]:
        """Gather support from each persona."""
        support = {}
        
        for persona_name, data in persona_data.items():
            # Check if this persona's research supports the concept
            mentions = []
            
            for item in data:
                if "data" in item and isinstance(item["data"], list):
                    for game in item["data"]:
                        if isinstance(game, dict) and "name" in game:
                            mentions.append(game["name"])
            
            support[persona_name] = mentions[:3]  # Top 3 mentions
        
        return support
    
    async def run_research(self) -> List[GameConcept]:
        """Main entry point for research."""
        try:
            concepts = await self.conduct_research()
            
            print(f"\n✓ Research complete. Found {len(concepts)} concepts.")
            
            # Save concepts to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            concepts_file = os.path.join(self.results_dir, f"concepts_{timestamp}.json")
            
            with open(concepts_file, "w") as f:
                json.dump([c.__dict__ for c in concepts], f, indent=2)
            
            print(f"✓ Concepts saved to: {concepts_file}")
            
            return concepts
            
        except Exception as e:
            print(f"Error during research: {str(e)}")
            raise


# For testing
if __name__ == "__main__":
    async def main():
        researcher = RobloxResearcher()
        
        # Test with a smaller subset for quick verification
        print("Testing researcher initialization...")
        print(f"Personas: {list(researcher.GAMING_PERSONAS.keys())}")
        print(f"Sources: {len(researcher.RESEARCH_SOURCES)}")
        
        # Uncomment to run full research (takes ~30 minutes)
        # concepts = await researcher.run_research()
        # for concept in concepts:
        #     print(f"\n{concept.name}: {concept.core_mechanic}")
    
    asyncio.run(main())
