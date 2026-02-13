#!/usr/bin/env python3
"""
Podcast RSS Feed Generator for Digg Daily

Generates a podcast-compatible RSS 2.0 feed with iTunes podcast extensions
that can be consumed by any podcast player.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.dom import minidom

from scraper import DiggDailyAPI, Episode


class PodcastFeedGenerator:
    """Generates podcast-compatible RSS feeds."""
    
    # Podcast metadata
    PODCAST_TITLE = "Digg Daily (Official AI Version)"
    PODCAST_DESCRIPTION = """
    Unofficial podcast feed for Digg Daily - the official AI-generated daily news digest from Digg.com.
    
    This feed pulls directly from Digg's official API - the same source used by the Digg Daily player 
    on the website. Updated automatically with each new episode.
    
    Digg Daily is an AI-hosted show that summarizes trending stories and community discussions from Digg 
    each day. Episodes are typically 5 minutes long.
    
    The /diggdaily community (digg.com/diggdaily) is curated by @roland and is not officially 
    maintained by digg.com. Thanks roland!
    
    This feed is created by @pixelnated and is not officially affiliated with digg.com.
    Content created by Digg. Feed aggregator is community-created.
    """.strip()
    PODCAST_LINK = "https://digg.com/diggdaily"
    PODCAST_AUTHOR = "Digg"
    PODCAST_LANGUAGE = "en-us"
    PODCAST_CATEGORY = "News"
    PODCAST_SUBCATEGORY = "Daily News"
    PODCAST_IMAGE = "https://pixelnated.github.io/digg-daily-rss/images/digg-daily-rss-logo.jpeg"
    PODCAST_EXPLICIT = "false"
    
    # iTunes namespace
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    ATOM_NS = "http://www.w3.org/2005/Atom"
    
    def __init__(self, output_dir: Path = None, feed_url: str = None):
        self.output_dir = output_dir or Path(__file__).parent / "output"
        self.output_dir.mkdir(exist_ok=True)
        self.feed_url = feed_url  # Self-referencing URL for Atom link
        
        # Register namespaces
        ET.register_namespace("itunes", self.ITUNES_NS)
        ET.register_namespace("atom", self.ATOM_NS)
    
    def _create_text_element(self, parent: ET.Element, tag: str, text: str, 
                              ns: str = None, **attrs) -> ET.Element:
        """Create a text element with optional namespace and attributes."""
        if ns:
            tag = f"{{{ns}}}{tag}"
        elem = ET.SubElement(parent, tag, **attrs)
        elem.text = text
        return elem
    
    def generate_feed(self, episodes: list[Episode]) -> str:
        """Generate a podcast-compatible RSS feed from episodes."""
        
        # Create root RSS element
        # Namespaces are handled by register_namespace in __init__
        rss = ET.Element("rss")
        rss.set("version", "2.0")
        
        channel = ET.SubElement(rss, "channel")
        
        # Basic channel elements
        self._create_text_element(channel, "title", self.PODCAST_TITLE)
        self._create_text_element(channel, "link", self.PODCAST_LINK)
        self._create_text_element(channel, "description", self.PODCAST_DESCRIPTION)
        self._create_text_element(channel, "language", self.PODCAST_LANGUAGE)
        self._create_text_element(channel, "copyright", 
                                   f"Content © Digg {datetime.now().year}")
        self._create_text_element(channel, "lastBuildDate", 
                                   datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"))
        self._create_text_element(channel, "generator", "Digg Daily RSS Generator")
        
        # Atom self-link (required by some podcast apps)
        if self.feed_url:
            ET.SubElement(channel, f"{{{self.ATOM_NS}}}link", {
                "href": self.feed_url,
                "rel": "self",
                "type": "application/rss+xml"
            })
        
        # iTunes-specific elements
        self._create_text_element(channel, "author", self.PODCAST_AUTHOR, self.ITUNES_NS)
        self._create_text_element(channel, "summary", self.PODCAST_DESCRIPTION, self.ITUNES_NS)
        self._create_text_element(channel, "explicit", self.PODCAST_EXPLICIT, self.ITUNES_NS)
        self._create_text_element(channel, "type", "episodic", self.ITUNES_NS)
        
        # iTunes owner
        owner = ET.SubElement(channel, f"{{{self.ITUNES_NS}}}owner")
        self._create_text_element(owner, "name", "Digg Daily Feed", self.ITUNES_NS)
        
        # iTunes category
        category = ET.SubElement(channel, f"{{{self.ITUNES_NS}}}category", text=self.PODCAST_CATEGORY)
        ET.SubElement(category, f"{{{self.ITUNES_NS}}}category", text=self.PODCAST_SUBCATEGORY)
        
        # iTunes image
        ET.SubElement(channel, f"{{{self.ITUNES_NS}}}image", href=self.PODCAST_IMAGE)
        
        # Standard RSS image
        image = ET.SubElement(channel, "image")
        self._create_text_element(image, "url", self.PODCAST_IMAGE)
        self._create_text_element(image, "title", self.PODCAST_TITLE)
        self._create_text_element(image, "link", self.PODCAST_LINK)
        
        # Add episodes as items
        for episode in episodes:
            self._add_episode_item(channel, episode)
        
        # Convert to string with proper formatting
        xml_string = ET.tostring(rss, encoding="unicode", method="xml")
        
        # Add XML declaration and namespace declarations
        # ET doesn't always add xmlns to root, so we inject them
        xml_string = xml_string.replace(
            '<rss version="2.0">',
            f'<rss version="2.0" xmlns:itunes="{self.ITUNES_NS}" xmlns:atom="{self.ATOM_NS}">'
        )
        
        # Pretty print
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding=None)
        
        # Remove extra blank lines that minidom adds
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _add_episode_item(self, channel: ET.Element, episode: Episode) -> None:
        """Add an episode as an RSS item."""
        
        item = ET.SubElement(channel, "item")
        
        # Basic item elements
        self._create_text_element(item, "title", episode.title)
        self._create_text_element(item, "link", episode.digg_url)
        self._create_text_element(item, "description", episode.description)
        self._create_text_element(item, "pubDate", episode.pub_date_rfc2822)
        self._create_text_element(item, "guid", episode.guid, isPermaLink="false")
        
        # Audio enclosure (required for podcasts)
        file_size = getattr(episode, 'file_size', 5000000)  # Default ~5MB
        ET.SubElement(item, "enclosure", {
            "url": episode.audio_url,
            "type": "audio/mpeg",
            "length": str(file_size)
        })
        
        # iTunes-specific episode elements
        self._create_text_element(item, "author", self.PODCAST_AUTHOR, self.ITUNES_NS)
        self._create_text_element(item, "summary", episode.description, self.ITUNES_NS)
        self._create_text_element(item, "explicit", self.PODCAST_EXPLICIT, self.ITUNES_NS)
        self._create_text_element(item, "episodeType", "full", self.ITUNES_NS)
        
        # Episode artwork (uses same image as podcast)
        ET.SubElement(item, f"{{{self.ITUNES_NS}}}image", href=self.PODCAST_IMAGE)
        
        # Duration (format: HH:MM:SS or MM:SS)
        minutes = episode.duration_seconds // 60
        seconds = episode.duration_seconds % 60
        duration_str = f"{minutes}:{seconds:02d}"
        self._create_text_element(item, "duration", duration_str, self.ITUNES_NS)
    
    def save_feed(self, episodes: list[Episode], filename: str = "feed.xml") -> Path:
        """Generate and save the feed to a file."""
        feed_content = self.generate_feed(episodes)
        output_path = self.output_dir / filename
        output_path.write_text(feed_content)
        return output_path


def main():
    """Generate the podcast feed."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Digg Daily podcast feed")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum episodes to include (default: 50)")
    parser.add_argument("--output", type=str, default="feed.xml",
                        help="Output filename (default: feed.xml)")
    args = parser.parse_args()
    
    print("Digg Daily Podcast Feed Generator")
    print("=" * 40)
    
    # Fetch episodes from official API
    print(f"\nFetching episodes from Digg Daily API...")
    api = DiggDailyAPI()
    episodes = api.fetch_episodes()
    
    # Limit number of episodes
    if args.limit and len(episodes) > args.limit:
        episodes = episodes[:args.limit]
    
    print(f"Found {len(episodes)} episodes")
    
    if not episodes:
        print("No episodes found. Check if the API is accessible.")
        return
    
    # Generate feed
    print("\nGenerating podcast feed...")
    generator = PodcastFeedGenerator()
    output_path = generator.save_feed(episodes, filename=args.output)
    
    print(f"\nFeed saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")
    
    # Print first episode info
    if episodes:
        ep = episodes[0]
        print(f"\nLatest episode: Episode {ep.episode_number}")
        print(f"  Date: {ep.date}")
        print(f"  Audio URL: {ep.audio_url}")
    
    print("\nTo use this feed:")
    print("1. Host the feed.xml file on a web server (GitHub Pages, Netlify, etc.)")
    print("2. Copy the URL to your podcast app")
    print("3. Add as a custom RSS feed")


if __name__ == "__main__":
    main()
