const STORAGE_KEY = "bookmarkManagerUrl";

function getManagerUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEY], (res) => resolve(res[STORAGE_KEY] || ""));
  });
}

function notify(message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: "Bookmark Manager",
    message
  });
}

async function openInManager(pageUrl, pageTitle) {
  const managerUrl = await getManagerUrl();
  if (!managerUrl) {
    notify("Najprv nastav cestu k Bookmark Manager v nastaveniach rozšírenia.");
    chrome.runtime.openOptionsPage();
    return;
  }
  if (!pageUrl) return;

  const base = managerUrl.split("?")[0].split("#")[0];
  const sep = "?";
  const target = base + sep + "add=" + encodeURIComponent(pageUrl) + "&title=" + encodeURIComponent(pageTitle || "");

  chrome.tabs.query({}, (tabs) => {
    const existing = tabs.find((t) => t.url && t.url.split("?")[0].split("#")[0] === base);
    if (existing) {
      chrome.tabs.update(existing.id, { url: target, active: true });
      chrome.windows.update(existing.windowId, { focused: true });
    } else {
      chrome.tabs.create({ url: target });
    }
  });
}

chrome.action.onClicked.addListener((tab) => {
  openInManager(tab.url, tab.title);
});

chrome.commands.onCommand.addListener((command) => {
  if (command !== "save-current-page") return;
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) openInManager(tabs[0].url, tabs[0].title);
  });
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "Uložiť túto stránku do Bookmark Manager",
    contexts: ["page"]
  });
  chrome.contextMenus.create({
    id: "save-link",
    title: "Uložiť odkaz do Bookmark Manager",
    contexts: ["link"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "save-page") {
    openInManager(tab.url, tab.title);
    return;
  }
  if (info.menuItemId === "save-link" && info.linkUrl) {
    chrome.scripting
      .executeScript({
        target: { tabId: tab.id },
        func: (href) => {
          const links = Array.from(document.querySelectorAll("a[href]"));
          const match = links.find((a) => a.href === href);
          return match ? match.textContent.trim() : "";
        },
        args: [info.linkUrl]
      })
      .then((results) => {
        const linkText = (results && results[0] && results[0].result) || "";
        openInManager(info.linkUrl, linkText);
      })
      .catch(() => openInManager(info.linkUrl, ""));
  }
});
