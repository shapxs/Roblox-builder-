#!/usr/bin/env python3
"""
Forge Builder - Start Script

Usage:
    python start.py              # Run immediately (development)
    python start.py --schedule   # Schedule for 8 PM daily (production)

Environment Variables:
    OLLAMA_BASE_URL=http://localhost:11434
    TELEGRAM_BOT_TOKEN=your_token
    TELEGRAM_CHAT_ID=your_chat_id
"""

import os
import sys
import time
from datetime import datetime, timedelta
import argparse

# Add forge to path
sys.path.insert(0, os.path.expanduser("~/forge"))

from night_agent.agent import NightAgent


def run_immediately():
    """Run the night agent immediately."""
    print("="*60)
    print("FORGE BUILDER - Starting")
    print("="*60)
    
    # Initialize and run
    agent = NightAgent()
    agent.run()


def schedule_daily():
    """Schedule the night agent to run at 8 PM daily."""
    print("="*60)
    print("FORGE BUILDER - Scheduled Mode")
    print("="*60)
    print("\nAgent will run at 8:00 PM ET every day")
    
    while True:
        now = datetime.now()
        
        # Calculate next 8 PM
        today_8pm = now.replace(hour=20, minute=0, second=0, microsecond=0)
        
        if now > today_8pm:
            # Already passed 8 PM today, schedule for tomorrow
            tomorrow = now + timedelta(days=1)
            next_run = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)
        else:
            # Still before 8 PM today
            next_run = today_8pm
        
        wait_seconds = (next_run - now).total_seconds()
        
        print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting for {wait_seconds/3600:.1f} hours...")
        
        # Wait until next run
        time.sleep(wait_seconds)
        
        # Run the agent
        print("\n" + "="*60)
        print("TIME TO RUN - Starting Night Agent")
        print("="*60)
        
        try:
            agent = NightAgent()
            agent.run()
            
            print("\nNight agent completed. Waiting for next day...")
            
        except Exception as e:
            print(f"\nError during night agent run: {str(e)}")
            print("Waiting for next scheduled time...")


def main():
    parser = argparse.ArgumentParser(
        description="Forge Builder - Autonomous Roblox Game Studio"
    )
    
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Schedule daily runs at 8 PM (production mode)"
    )
    
    args = parser.parse_args()
    
    if args.schedule:
        schedule_daily()
    else:
        run_immediately()


if __name__ == "__main__":
    main()
