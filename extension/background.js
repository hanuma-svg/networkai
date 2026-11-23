// NetworkAI Side Panel Background Service Worker
// Enables native side panel behavior on action icon click
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.warn("[NetworkAI] setPanelBehavior error:", err));

chrome.runtime.onInstalled.addListener(() => {
  console.log("[NetworkAI] LinkedIn Side Panel extension installed.");
});
