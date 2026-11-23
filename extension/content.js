// NetworkAI LinkedIn Content Script
// Safely extracts profile (name, headline, about, recent activity) or post text + URL without automated loops

function extractLinkedInContext() {
  const url = window.location.href;
  const isProfile = url.includes("/in/");
  const isPost = url.includes("/posts/") || url.includes("/feed/update/");

  let name = "";
  let headline = "";
  let company = "";
  let location = "";
  let about = "";
  let recentPostText = "";

  if (isProfile) {
    // Name extraction
    const nameEl = document.querySelector(
      "h1.text-heading-xl, .pv-top-card--list .inline, .top-card-layout__title, .artdeco-entity-lockup__title"
    );
    name = nameEl ? nameEl.textContent.trim() : "";

    // Headline extraction
    const headlineEl = document.querySelector(
      ".text-body-medium.break-words, .pv-text-details__left-panel .text-body-medium, .top-card-layout__headline"
    );
    headline = headlineEl ? headlineEl.textContent.trim() : "";

    // Company extraction
    const companyEl = document.querySelector(
      ".pv-text-details__right-panel .inline-show-more-text, .experience-item__subtitle, [aria-label='Current company']"
    );
    company = companyEl ? companyEl.textContent.trim() : "";

    // Location extraction
    const locEl = document.querySelector(
      ".pv-text-details__left-panel .text-body-small.inline, .top-card-layout__first-subline"
    );
    location = locEl ? locEl.textContent.trim() : "";

    // About section extraction
    const aboutEl = document.querySelector(
      "#about ~ .display-flex .inline-show-more-text, .pv-about-section .inline-show-more-text"
    );
    about = aboutEl ? aboutEl.textContent.trim() : "";

    // Recent activity snippet
    const postSnippet = document.querySelector(
      ".update-components-text, .feed-shared-update-v2__description"
    );
    recentPostText = postSnippet ? postSnippet.textContent.trim() : "";
  } else if (isPost) {
    // Post author
    const authorEl = document.querySelector(
      ".update-components-actor__name, .feed-shared-actor__name"
    );
    name = authorEl ? authorEl.textContent.trim() : "";

    const authorHeadlineEl = document.querySelector(
      ".update-components-actor__description, .feed-shared-actor__description"
    );
    headline = authorHeadlineEl ? authorHeadlineEl.textContent.trim() : "";

    // Post commentary text
    const textEl = document.querySelector(
      ".update-components-text, .feed-shared-update-v2__description, .feed-shared-text"
    );
    recentPostText = textEl ? textEl.textContent.trim() : "";
  } else {
    // General feed / search context
    const firstPost = document.querySelector(".feed-shared-update-v2");
    if (firstPost) {
      const author = firstPost.querySelector(".update-components-actor__name");
      const desc = firstPost.querySelector(".update-components-text");
      name = author ? author.textContent.trim() : "";
      recentPostText = desc ? desc.textContent.trim() : "";
    }
  }

  // Fallback to page title if name was not detected
  if (!name && document.title) {
    const clean = document.title
      .replace(/\|.*$/i, "")
      .replace(/LinkedIn/gi, "")
      .trim();
    if (clean) name = clean;
  }

  return {
    url,
    full_name: name || "LinkedIn Professional",
    headline,
    company,
    location,
    about,
    recent_post_text: recentPostText || about,
  };
}

// Runtime message listener for the side panel
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "EXTRACT_PAGE_CONTEXT") {
    try {
      const context = extractLinkedInContext();
      sendResponse({ status: "success", data: context });
    } catch (err) {
      sendResponse({ status: "error", error: err.message });
    }
  }
  return true;
});
