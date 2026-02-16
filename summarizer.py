#!/usr/bin/env python3
"""
Episode Summarizer for Digg Daily RSS

Transcribes MP3 audio using local Whisper model and generates summaries.
This is a FREE solution that runs entirely on GitHub Actions - no API costs.

Feature Flag: Set ENABLE_SUMMARIES=true to enable, or false/unset to disable.
This allows easy rollback if issues arise.

Dependencies: openai-whisper, ffmpeg (system package)
"""

import os
import json
import hashlib
import tempfile
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import requests

# Feature flag - easily disable if needed
ENABLE_SUMMARIES = os.environ.get("ENABLE_SUMMARIES", "false").lower() == "true"

# Whisper model size - "tiny" is fastest, "base" is better quality
# tiny: ~1GB RAM, ~30sec for 5min audio
# base: ~1.5GB RAM, ~60sec for 5min audio
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "tiny")

# Cache directory for transcripts and summaries
CACHE_DIR = Path(__file__).parent / "cache" / "summaries"


@dataclass
class EpisodeSummary:
    """Contains transcript and summary for an episode."""
    episode_id: str
    transcript: str
    summary: str
    model_used: str
    

class Summarizer:
    """
    Transcribes and summarizes podcast episodes using local models.
    
    This runs entirely locally - no API costs. Uses OpenAI's Whisper
    model (MIT license) for transcription and extractive summarization.
    """
    
    def __init__(self, cache_dir: Path = None, model_size: str = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_size = model_size or WHISPER_MODEL
        self._model = None  # Lazy load
    
    @property
    def model(self):
        """Lazy load the Whisper model to avoid loading if not needed."""
        if self._model is None:
            import whisper
            print(f"Loading Whisper '{self.model_size}' model...")
            self._model = whisper.load_model(self.model_size)
            print("Model loaded successfully.")
        return self._model
    
    def _get_cache_path(self, episode_id: str) -> Path:
        """Get the cache file path for an episode."""
        safe_id = hashlib.md5(episode_id.encode()).hexdigest()[:16]
        return self.cache_dir / f"{safe_id}.json"
    
    def _load_from_cache(self, episode_id: str) -> Optional[EpisodeSummary]:
        """Load cached summary if available."""
        cache_path = self._get_cache_path(episode_id)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                return EpisodeSummary(**data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    def _save_to_cache(self, summary: EpisodeSummary) -> None:
        """Save summary to cache."""
        cache_path = self._get_cache_path(summary.episode_id)
        cache_path.write_text(json.dumps(asdict(summary), indent=2))
    
    def download_audio(self, audio_url: str, episode_id: str) -> Optional[Path]:
        """Download MP3 to temp file for processing."""
        try:
            print(f"Downloading audio: {audio_url[:80]}...")
            response = requests.get(audio_url, timeout=120, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            temp_dir = Path(tempfile.gettempdir()) / "digg_daily_audio"
            temp_dir.mkdir(exist_ok=True)
            
            audio_path = temp_dir / f"{episode_id}.mp3"
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded: {audio_path.stat().st_size / 1024 / 1024:.1f} MB")
            return audio_path
            
        except requests.RequestException as e:
            print(f"Error downloading audio: {e}")
            return None
    
    def transcribe(self, audio_path: Path) -> str:
        """Transcribe audio file using Whisper."""
        print(f"Transcribing with Whisper ({self.model_size} model)...")
        
        result = self.model.transcribe(
            str(audio_path),
            language="en",
            fp16=False,  # CPU doesn't support fp16
        )
        
        transcript = result["text"].strip()
        print(f"Transcription complete: {len(transcript)} characters")
        return transcript
    
    def extract_summary(self, transcript: str, max_sentences: int = 5) -> str:
        """
        Generate a summary using extractive summarization.
        
        This is a simple, fast, zero-cost approach that:
        1. Splits transcript into sentences
        2. Scores sentences by importance (position, keywords, length)
        3. Returns top sentences in original order
        
        No heavy ML models required - just smart text processing.
        """
        if not transcript:
            return ""
        
        # Clean up transcript
        text = re.sub(r'\s+', ' ', transcript).strip()
        
        # Split into sentences (handle common abbreviations)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if len(sentences) <= max_sentences:
            return text
        
        # Score each sentence
        scored = []
        for i, sentence in enumerate(sentences):
            score = 0
            
            # Position bonus: first and last sentences often contain key info
            if i == 0:
                score += 3
            elif i == len(sentences) - 1:
                score += 2
            elif i < 3:
                score += 1
            
            # Length bonus: medium length sentences are often more informative
            word_count = len(sentence.split())
            if 10 <= word_count <= 30:
                score += 2
            elif 8 <= word_count <= 40:
                score += 1
            
            # Keyword bonus: news-related important words
            keywords = [
                'today', 'breaking', 'announced', 'report', 'according',
                'major', 'significant', 'important', 'new', 'latest',
                'says', 'said', 'claims', 'reveals', 'shows',
                'first', 'top', 'biggest', 'million', 'billion'
            ]
            sentence_lower = sentence.lower()
            for kw in keywords:
                if kw in sentence_lower:
                    score += 1
            
            # Penalty for questions (they're usually rhetorical in news)
            if '?' in sentence:
                score -= 1
            
            scored.append((i, score, sentence))
        
        # Sort by score, take top sentences
        scored.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored[:max_sentences]
        
        # Re-sort by original position to maintain narrative flow
        top_sentences.sort(key=lambda x: x[0])
        
        summary = ' '.join(s[2] for s in top_sentences)
        return summary
    
    def summarize_episode(self, episode_id: str, audio_url: str, 
                          force_refresh: bool = False) -> Optional[EpisodeSummary]:
        """
        Generate summary for an episode.
        
        Args:
            episode_id: Unique episode identifier
            audio_url: URL to MP3 file
            force_refresh: If True, ignore cache and regenerate
            
        Returns:
            EpisodeSummary object or None if failed
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_from_cache(episode_id)
            if cached:
                print(f"Using cached summary for {episode_id}")
                return cached
        
        # Download audio
        audio_path = self.download_audio(audio_url, episode_id)
        if not audio_path:
            return None
        
        try:
            # Transcribe
            transcript = self.transcribe(audio_path)
            
            # Generate summary
            summary = self.extract_summary(transcript, max_sentences=4)
            
            # Create result
            result = EpisodeSummary(
                episode_id=episode_id,
                transcript=transcript,
                summary=summary,
                model_used=f"whisper-{self.model_size}"
            )
            
            # Cache it
            self._save_to_cache(result)
            
            return result
            
        finally:
            # Clean up downloaded audio
            if audio_path.exists():
                audio_path.unlink()
    
    def summarize_episodes(self, episodes: list, limit: int = 5) -> dict[str, EpisodeSummary]:
        """
        Summarize multiple episodes, using cache when available.
        
        This method efficiently handles caching:
        - Cached episodes are loaded instantly (no download/transcription)
        - Only NEW episodes count toward the transcription limit
        - This means subsequent runs are fast once cache is built
        
        Args:
            episodes: List of Episode objects with episode_id and audio_url
            limit: Maximum number of NEW episodes to transcribe per run
            
        Returns:
            Dict mapping episode_id to EpisodeSummary
        """
        results = {}
        new_transcriptions = 0
        
        for i, episode in enumerate(episodes):
            # Check if already cached (fast path)
            cached = self._load_from_cache(episode.episode_id)
            if cached:
                print(f"[{i+1}/{len(episodes)}] Cached: episode {episode.episode_id}")
                results[episode.episode_id] = cached
                continue
            
            # New episode - check if we've hit transcription limit
            if new_transcriptions >= limit:
                print(f"[{i+1}/{len(episodes)}] Skipped: transcription limit ({limit}) reached")
                continue
            
            # Transcribe new episode
            print(f"\n[{i+1}/{len(episodes)}] Transcribing NEW episode {episode.episode_id}...")
            summary = self.summarize_episode(episode.episode_id, episode.audio_url)
            if summary:
                results[episode.episode_id] = summary
                new_transcriptions += 1
        
        print(f"\nSummary: {len(results)} total, {new_transcriptions} newly transcribed")
        return results


def is_enabled() -> bool:
    """Check if summarization is enabled."""
    return ENABLE_SUMMARIES


def main():
    """Test the summarizer with a sample episode."""
    print("Digg Daily Episode Summarizer")
    print("=" * 40)
    print(f"Feature enabled: {ENABLE_SUMMARIES}")
    print(f"Whisper model: {WHISPER_MODEL}")
    
    if not ENABLE_SUMMARIES:
        print("\nSummarization is DISABLED.")
        print("Set ENABLE_SUMMARIES=true to enable.")
        return
    
    # Test with latest episode
    from scraper import DiggDailyAPI
    
    api = DiggDailyAPI()
    episodes = api.fetch_episodes()
    
    if not episodes:
        print("No episodes found.")
        return
    
    # Summarize latest episode
    summarizer = Summarizer()
    latest = episodes[0]
    
    print(f"\nProcessing: {latest.title}")
    summary = summarizer.summarize_episode(latest.episode_id, latest.audio_url)
    
    if summary:
        print(f"\n{'='*40}")
        print("TRANSCRIPT (first 500 chars):")
        print(summary.transcript[:500] + "...")
        print(f"\n{'='*40}")
        print("SUMMARY:")
        print(summary.summary)
    else:
        print("Failed to generate summary.")


if __name__ == "__main__":
    main()
