/**
 * Digg Daily Player - Background Service Worker
 * 
 * Handles optional background tasks like checking for new episodes
 * and updating the badge.
 */

// Check for updates periodically
const CHECK_INTERVAL_MINUTES = 60;

// Listen for installation
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Digg Daily Player installed:', details.reason);
  
  // Set up periodic alarm for checking updates
  chrome.alarms.create('checkForNewEpisode', {
    periodInMinutes: CHECK_INTERVAL_MINUTES
  });
});

// Handle alarms
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'checkForNewEpisode') {
    console.log('Checking for new Digg Daily episode...');
    // The actual check happens when the popup is opened
    // This alarm is here for future badge notification feature
  }
});

// Handle messages from popup or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_LATEST_EPISODE') {
    // Could implement background fetch here
    sendResponse({ status: 'use_popup' });
  }
  
  return true; // Keep channel open for async response
});
