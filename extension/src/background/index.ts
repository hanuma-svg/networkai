// Chrome Extension Background Service Worker
chrome.runtime.onInstalled.addListener(() => {
  console.log("[NetworkAI] Background service worker initialized.");
});

// Listener for messages from content script or popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "PING") {
    sendResponse({ status: "PONG", timestamp: Date.now() });
  }
  return true;
});
