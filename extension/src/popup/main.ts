// Chrome Extension Popup Script
document.addEventListener("DOMContentLoaded", () => {
  const statusEl = document.getElementById("status");
  if (statusEl) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab?.url?.includes("linkedin.com")) {
        statusEl.textContent = "Active on LinkedIn profile/feed.";
      } else {
        statusEl.textContent = "Navigate to LinkedIn to activate co-pilot.";
      }
    });
  }
});
