// Chrome Extension Content Script
console.log("[NetworkAI] Content script injected on LinkedIn.");

// Listener for runtime messages from popup or background worker
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "GET_PAGE_CONTEXT") {
    sendResponse({
      url: window.location.href,
      title: document.title,
    });
  }
  return true;
});
