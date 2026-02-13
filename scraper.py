#!/usr/bin/env python3
"""
Digg Daily RSS Feed Generator

Fetches episodes directly from Digg's official API endpoint.
No scraping required - uses the same API as the Digg Daily player widget.
"""

import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import requests


# Official Digg Daily API endpoints
DIGG_DAILY_API = "https://sxuww3gfy4.execute-api.us-east-2.amazonaws.com/prod/episodes"
DIGG_DAILY_CDN = "https://d3tha58ojcqcpf.cloudfront.net/prod/episodes"


@dataclass
class Episode:
    """Represents a Digg Daily podcast episode."""
    episode_id: str
    episode_number: int
    title: str
    date: str  # ISO format YYYY-MM-DD
    published_date: str  # Full ISO datetime
    published_state: str  # PUBLISHED or DRAFT
    file_name: str
    description: str = ""
    duration_seconds: int = 300  # Default 5 minutes
    
    @property
    def guid(self) -> str:
        """Generate a unique ID for this episode."""
        return self.episode_id
    
    @property
    def audio_url(self) -> str:
        """Get the direct audio URL from Digg's CloudFront CDN."""
        return f"{DIGG_DAILY_CDN}/{self.episode_id}/{self.file_name}"
    
    @property
    def pub_date_rfc2822(self) -> str:
        """Return the publication date in RFC 2822 format for RSS."""
        try:
            dt = datetime.fromisoformat(self.published_date.replace('Z', '+00:00'))
            return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except ValueError:
            return datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    @property
    def digg_url(self) -> str:
        """Link to Digg homepage (episodes don't have individual pages)."""
        return "https://digg.com"


class DiggDailyAPI:
    """Client for the official Digg Daily API."""
    
    USER_AGENT = "DiggDailyRSS/2.0 (Podcast Feed Generator)"
    
    def __init__(self, cache_dir: Path = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        })
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
    
    def fetch_episodes(self) -> list[Episode]:
        """
        Fetch episodes from the official Digg Daily API.
        
        Returns:
            List of Episode objects sorted by date (newest first).
        """
        try:
            response = self.session.get(DIGG_DAILY_API, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"Error fetching from API: {e}")
            return self._load_cached_episodes()
        except json.JSONDecodeError as e:
            print(f"Error parsing API response: {e}")
            return self._load_cached_episodes()
        
        episodes = []
        for ep_data in data.get("episodes", []):
            episode = self._parse_episode(ep_data)
            if episode:
                episodes.append(episode)
        
        # Sort by date (newest first)
        episodes.sort(key=lambda e: e.published_date, reverse=True)
        
        # Cache the results
        self._cache_episodes(episodes)
        
        return episodes
    
    def _parse_episode(self, data: dict) -> Optional[Episode]:
        """Parse episode data from API response."""
        try:
            episode_id = data["episode_id"]
            episode_number = int(data.get("episode_number", 0))
            file_name = data["file_name"]
            published_date = data["published_date"]
            published_state = data.get("published_state", "DRAFT")
            
            # Extract date from filename: DiggDaily_2026-02-13_093616_final.mp3
            date_match = re.search(r"DiggDaily_(\d{4}-\d{2}-\d{2})", file_name)
            if date_match:
                date = date_match.group(1)
            else:
                # Fallback to published_date
                date = published_date[:10]
            
            # Format title
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = dt.strftime("%B %d, %Y")
                title = f"Digg Daily for {formatted_date}"
            except ValueError:
                title = f"Digg Daily - Episode {episode_number}"
            
            # Description
            description = f"Digg Daily for {formatted_date}."
            
            return Episode(
                episode_id=episode_id,
                episode_number=episode_number,
                title=title,
                date=date,
                published_date=published_date,
                published_state=published_state,
                file_name=file_name,
                description=description,
            )
        except (KeyError, ValueError) as e:
            print(f"Error parsing episode: {e}")
            return None
    
    def _cache_episodes(self, episodes: list[Episode]) -> None:
        """Cache episodes to disk."""
        cache_file = self.cache_dir / "episodes.json"
        data = [asdict(e) for e in episodes]
        cache_file.write_text(json.dumps(data, indent=2))
    
    def _load_cached_episodes(self) -> list[Episode]:
        """Load episodes from cache."""
        cache_file = self.cache_dir / "episodes.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return [Episode(**e) for e in data]
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading cache: {e}")
        return []
    
    def get_latest_episode(self) -> Optional[Episode]:
        """Get the most recent episode."""
        episodes = self.fetch_episodes()
        return episodes[0] if episodes else None


# Backwards compatibility alias
DiggDailyScraper = DiggDailyAPI


def main():
    """Test the API client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch Digg Daily episodes from official API")
    parser.add_argument("--limit", type=int, default=10,
                        help="Maximum episodes to display (default: 10)")
    parser.add_argument("--verify", action="store_true",
                        help="Verify audio URLs are accessible")
    args = parser.parse_args()
    
    print("Digg Daily API Client")
    print("=" * 50)
    print(f"API Endpoint: {DIGG_DAILY_API}")
    print(f"CDN Endpoint: {DIGG_DAILY_CDN}")
    print()
    
    api = DiggDailyAPI()
    episodes = api.fetch_episodes()
    
    print(f"Found {len(episodes)} episodes:\n")
    
    for i, ep in enumerate(episodes[:args.limit]):
        print(f"  Episode {ep.episode_number}: {ep.title}")
        print(f"    Date: {ep.date}")
        print(f"    State: {ep.published_state}")
        print(f"    Audio: {ep.audio_url}")
        
        if args.verify:
            try:
                resp = api.session.head(ep.audio_url, timeout=10)
                size_mb = int(resp.headers.get('content-length', 0)) / 1024 / 1024
                print(f"    Status: {resp.status_code} ({size_mb:.1f} MB)")
            except Exception as e:
                print(f"    Status: Error - {e}")
        
        print()


if __name__ == "__main__":
    main()
