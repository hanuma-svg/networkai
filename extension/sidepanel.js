// NetworkAI Side Panel Logic with Configurable Backend URL
let API_URL = "http://localhost:8000";

let currentPageContext = null;
let currentActionId = null;
let currentActionType = "connection_note";

const targetNameEl = document.getElementById("target-name");
const targetHeadlineEl = document.getElementById("target-headline");
const targetUrlEl = document.getElementById("target-url");
const relevanceBadgeEl = document.getElementById("relevance-badge");
const analyzeBtn = document.getElementById("analyze-btn");
const hooksSection = document.getElementById("hooks-section");
const hooksContainer = document.getElementById("hooks-container");
const draftSection = document.getElementById("draft-section");
const draftTextarea = document.getElementById("draft-textarea");
const charCounter = document.getElementById("char-counter");
const actionTypePill = document.getElementById("action-type-pill");
const approveCopyBtn = document.getElementById("approve-copy-btn");
const refreshBtn = document.getElementById("refresh-context-btn");
const toastEl = document.getElementById("toast");
const connectionStatusEl = document.getElementById("connection-status");

// Settings Elements
const settingsToggleBtn = document.getElementById("settings-toggle-btn");
const settingsPanel = document.getElementById("settings-panel");
const apiUrlInput = document.getElementById("api-url-input");
const saveUrlBtn = document.getElementById("save-url-btn");
const setLocalBtn = document.getElementById("set-local-btn");
const testConnectionBtn = document.getElementById("test-connection-btn");
const currentEnvPill = document.getElementById("current-env-pill");

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  setTimeout(() => toastEl.classList.add("hidden"), 2500);
}

// 0. Load & Configure Backend API URL from Storage
async function loadApiUrl() {
  try {
    if (chrome && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get(["networkai_api_url"], (result) => {
        if (result && result.networkai_api_url) {
          API_URL = result.networkai_api_url.replace(/\/+$/, "");
          apiUrlInput.value = API_URL;
        } else {
          API_URL = "http://localhost:8000";
          apiUrlInput.value = API_URL;
        }
        updateEnvPill();
      });
    }
  } catch (err) {
    console.warn("Storage load error:", err);
  }
}

function updateEnvPill() {
  if (API_URL.includes("localhost") || API_URL.includes("127.0.0.1")) {
    currentEnvPill.textContent = "Local";
    currentEnvPill.style.color = "#94a3b8";
  } else {
    currentEnvPill.textContent = "Cloud (Railway)";
    currentEnvPill.style.color = "#38bdf8";
  }
}

// Settings Handlers
settingsToggleBtn.addEventListener("click", () => {
  settingsPanel.classList.toggle("hidden");
});

saveUrlBtn.addEventListener("click", () => {
  const newUrl = apiUrlInput.value.trim().replace(/\/+$/, "");
  if (!newUrl) return;
  API_URL = newUrl;
  if (chrome && chrome.storage && chrome.storage.local) {
    chrome.storage.local.set({ networkai_api_url: API_URL }, () => {
      showToast("API URL saved!");
      updateEnvPill();
    });
  } else {
    showToast("API URL updated!");
    updateEnvPill();
  }
});

setLocalBtn.addEventListener("click", () => {
  API_URL = "http://localhost:8000";
  apiUrlInput.value = API_URL;
  if (chrome && chrome.storage && chrome.storage.local) {
    chrome.storage.local.set({ networkai_api_url: API_URL });
  }
  updateEnvPill();
  showToast("Reset to localhost:8000");
});

testConnectionBtn.addEventListener("click", async () => {
  testConnectionBtn.disabled = true;
  testConnectionBtn.textContent = "Testing...";
  try {
    const res = await fetch(`${API_URL}/health`);
    if (res.ok) {
      const data = await res.json();
      showToast(`Connected! Service: ${data.service || "OK"}`);
      connectionStatusEl.textContent = "Online";
      connectionStatusEl.style.color = "#10b981";
    } else {
      showToast(`HTTP ${res.status}: Connection failed`);
      connectionStatusEl.textContent = "Error";
      connectionStatusEl.style.color = "#ef4444";
    }
  } catch (err) {
    showToast("Connection failed. Is server running?");
    connectionStatusEl.textContent = "Offline";
    connectionStatusEl.style.color = "#ef4444";
  } finally {
    testConnectionBtn.disabled = false;
    testConnectionBtn.textContent = "Test Connection";
  }
});

// 1. Fetch current tab context from LinkedIn content script
async function detectCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    if (!tab.url || !tab.url.includes("linkedin.com")) {
      targetNameEl.textContent = "Not on LinkedIn";
      targetHeadlineEl.textContent = "Navigate to a LinkedIn profile or post to analyze.";
      targetUrlEl.textContent = tab.url || "";
      analyzeBtn.disabled = true;
      return;
    }

    analyzeBtn.disabled = false;
    chrome.tabs.sendMessage(tab.id, { action: "EXTRACT_PAGE_CONTEXT" }, (response) => {
      if (chrome.runtime.lastError || !response || response.status !== "success") {
        targetNameEl.textContent = tab.title ? tab.title.split("|")[0].trim() : "LinkedIn User";
        targetHeadlineEl.textContent = "Ready to analyze profile";
        targetUrlEl.textContent = tab.url;
        currentPageContext = {
          full_name: targetNameEl.textContent,
          linkedin_url: tab.url,
          headline: "",
          recent_post_text: "",
        };
      } else {
        const data = response.data;
        currentPageContext = data;
        targetNameEl.textContent = data.full_name || "LinkedIn Professional";
        targetHeadlineEl.textContent = data.headline || data.company || "LinkedIn Profile";
        targetUrlEl.textContent = data.url;
      }
    });
  } catch (err) {
    console.error("detectCurrentTab error:", err);
  }
}

// 2. Character counter updater
function updateCharCounter() {
  const count = draftTextarea.value.length;
  const isConnectionNote = currentActionType === "connection_note";
  charCounter.textContent = isConnectionNote ? `${count}/300` : `${count} chars`;

  if (isConnectionNote && count > 300) {
    charCounter.classList.add("danger-text");
    draftTextarea.classList.add("danger-border");
  } else {
    charCounter.classList.remove("danger-text");
    draftTextarea.classList.remove("danger-border");
  }
}

draftTextarea.addEventListener("input", updateCharCounter);

// 3. Analyze Current Page -> POST ${API_URL}/api/analyze-profile
analyzeBtn.addEventListener("click", async () => {
  if (!currentPageContext) await detectCurrentTab();
  if (!currentPageContext) return;

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "✨ Analyzing with AI...";

  try {
    const res = await fetch(`${API_URL}/api/analyze-profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentPageContext),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const result = await res.json();
    const profiler = result.profiler_output;
    const actionItem = result.action_item;

    currentActionId = actionItem.id;
    currentActionType = actionItem.action_type;

    // Update Relevance Badge
    relevanceBadgeEl.textContent = `${profiler.relevance_score}% Match`;
    relevanceBadgeEl.classList.remove("badge-hidden");

    // Display Shared Hooks
    hooksContainer.innerHTML = "";
    (profiler.shared_hooks || []).forEach((hook) => {
      const tag = document.createElement("span");
      tag.className = "hook-tag";
      tag.textContent = `#${hook.replace(/^#/, "")}`;
      hooksContainer.appendChild(tag);
    });
    hooksSection.classList.remove("hidden");

    // Display Draft Textarea
    actionTypePill.textContent =
      currentActionType === "connection_note"
        ? "Connection Note"
        : currentActionType === "draft_comment"
        ? "Comment"
        : "Follow-Up";

    draftTextarea.value = actionItem.content;
    updateCharCounter();
    draftSection.classList.remove("hidden");

    showToast("Profile analyzed & draft generated!");
  } catch (err) {
    console.error("Analysis error:", err);
    showToast("Analysis failed: " + err.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "✨ Analyze Current Page";
  }
});

// 4. Approve & Copy Button -> POST ${API_URL}/api/queue/{id}/approve
approveCopyBtn.addEventListener("click", async () => {
  const content = draftTextarea.value;
  try {
    await navigator.clipboard.writeText(content);

    if (currentActionId) {
      fetch(`${API_URL}/api/queue/${currentActionId}/approve`, {
        method: "POST",
      }).catch((e) => console.warn("Approve background error:", e));
    }

    showToast("📋 Draft copied & approved!");
  } catch (err) {
    showToast("Clipboard copy failed.");
  }
});

refreshBtn.addEventListener("click", detectCurrentTab);

// Initialize on open
document.addEventListener("DOMContentLoaded", () => {
  loadApiUrl();
  detectCurrentTab();
});
