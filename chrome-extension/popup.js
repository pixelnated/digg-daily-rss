/**
 * Digg Daily Player - Popup Script
 * 
 * Fetches the latest official Digg Daily episode from Digg's API
 * and provides a simple audio player interface.
 */

const API_URL = 'https://sxuww3gfy4.execute-api.us-east-2.amazonaws.com/prod/episodes';
const CDN_BASE = 'https://d3tha58ojcqcpf.cloudfront.net/prod/episodes';
const DIGGDAILY_URL = 'https://digg.com/diggdaily';
const CACHE_KEY = 'diggDailyCache';
const CACHE_DURATION_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Format date from ISO string
 */
function formatDateFromISO(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

/**
 * Create a title from the published date
 */
function createTitle(publishedDate, episodeNumber) {
  const date = new Date(publishedDate);
  const month = date.toLocaleDateString('en-US', { month: 'long' });
  const day = date.getDate();
  const year = date.getFullYear();
  return `Digg Daily #${episodeNumber} - ${month} ${day}, ${year}`;
}

/**
 * Fetch the latest episode from Digg's official API
 */
async function fetchLatestEpisode() {
  // Check cache first
  const cached = await getCachedEpisode();
  if (cached) {
    console.log('Using cached episode:', cached.title);
    return cached;
  }
  
  console.log('Fetching from Digg Daily API...');
  
  const response = await fetch(API_URL);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  const data = await response.json();
  
  if (!data.episodes || data.episodes.length === 0) {
    throw new Error('No episodes available');
  }
  
  // Find the latest PUBLISHED episode
  const publishedEpisodes = data.episodes.filter(ep => ep.published_state === 'PUBLISHED');
  
  if (publishedEpisodes.length === 0) {
    throw new Error('No published episodes found');
  }
  
  // Sort by published_date descending
  publishedEpisodes.sort((a, b) => new Date(b.published_date) - new Date(a.published_date));
  
  const latest = publishedEpisodes[0];
  
  const audioUrl = `${CDN_BASE}/${latest.episode_id}/${latest.file_name}`;
  
  const episode = {
    title: createTitle(latest.published_date, latest.episode_number),
    date: latest.published_date.split('T')[0],
    episodeNumber: latest.episode_number,
    diggUrl: DIGGDAILY_URL,
    audioUrl: audioUrl,
    fetchedAt: Date.now()
  };
  
  // Cache the result
  await cacheEpisode(episode);
  
  return episode;
}

/**
 * Get cached episode if still valid
 */
async function getCachedEpisode() {
  try {
    const result = await chrome.storage.local.get(CACHE_KEY);
    const cached = result[CACHE_KEY];
    
    if (cached && (Date.now() - cached.fetchedAt) < CACHE_DURATION_MS) {
      return cached;
    }
  } catch (err) {
    console.warn('Cache read error:', err);
  }
  return null;
}

/**
 * Cache episode data
 */
async function cacheEpisode(episode) {
  try {
    await chrome.storage.local.set({ [CACHE_KEY]: episode });
  } catch (err) {
    console.warn('Cache write error:', err);
  }
}

/**
 * Clear cache (for refresh)
 */
async function clearCache() {
  try {
    await chrome.storage.local.remove(CACHE_KEY);
  } catch (err) {
    console.warn('Cache clear error:', err);
  }
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
  try {
    const date = new Date(dateStr + 'T12:00:00');
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

/**
 * Show the player with episode data
 */
function showPlayer(episode) {
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('error').classList.add('hidden');
  document.getElementById('player').classList.remove('hidden');
  
  document.getElementById('episode-title').textContent = episode.title;
  document.getElementById('episode-date').textContent = formatDate(episode.date);
  
  const audioPlayer = document.getElementById('audio-player');
  audioPlayer.src = episode.audioUrl;
  
  document.getElementById('digg-link').href = episode.diggUrl;
  document.getElementById('download-link').href = episode.audioUrl;
}

/**
 * Show error state
 */
function showError(message) {
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('player').classList.add('hidden');
  document.getElementById('error').classList.remove('hidden');
  
  document.getElementById('error-message').textContent = message;
}

/**
 * Initialize the popup
 */
async function init() {
  console.log('Digg Daily Player initializing...');
  
  // Set up refresh button
  document.getElementById('refresh-btn').addEventListener('click', async (e) => {
    e.preventDefault();
    document.getElementById('player').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');
    document.getElementById('loading').classList.remove('hidden');
    
    await clearCache();
    await loadEpisode();
  });
  
  await loadEpisode();
}

/**
 * Load and display the latest episode
 */
async function loadEpisode() {
  try {
    const episode = await fetchLatestEpisode();
    showPlayer(episode);
  } catch (err) {
    console.error('Failed to load episode:', err);
    showError(err.message);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
