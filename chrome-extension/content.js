/**
 * Digg Daily Player - Content Script
 * 
 * Enhances the digg.com experience by highlighting Digg Daily posts
 * and adding quick-play functionality.
 */

// Only run on digg.com
if (window.location.hostname.includes('digg.com')) {
  console.log('Digg Daily Player content script loaded');
  
  // Add a floating play button for quick access to today's episode
  function addQuickPlayButton() {
    // Check if already added
    if (document.getElementById('digg-daily-quick-play')) return;
    
    const button = document.createElement('button');
    button.id = 'digg-daily-quick-play';
    button.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <path d="M8 5v14l11-7z"/>
      </svg>
      <span>Daily</span>
    `;
    button.title = 'Play Today\'s Digg Daily';
    
    button.addEventListener('click', () => {
      // Open the extension popup (can't do directly, so navigate to diggdaily)
      window.open('https://digg.com/diggdaily', '_blank');
    });
    
    document.body.appendChild(button);
  }
  
  // Highlight official Digg Daily posts (not homemade recaps)
  function highlightOfficialPosts() {
    const links = document.querySelectorAll('a[href*="/diggdaily/"]');
    
    links.forEach(link => {
      const href = link.getAttribute('href') || '';
      
      // Check if it's an official Digg Daily post
      if (href.includes('/digg-daily-') && 
          !href.includes('homemade') && 
          !href.includes('recap')) {
        
        // Add visual indicator
        const container = link.closest('article') || link.closest('div');
        if (container && !container.classList.contains('digg-daily-official')) {
          container.classList.add('digg-daily-official');
        }
      }
    });
  }
  
  // Run when page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      addQuickPlayButton();
      highlightOfficialPosts();
    });
  } else {
    addQuickPlayButton();
    highlightOfficialPosts();
  }
  
  // Also watch for dynamic content loading
  const observer = new MutationObserver(() => {
    highlightOfficialPosts();
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}
