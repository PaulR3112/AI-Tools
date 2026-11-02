const STORAGE_KEY = "bookmarkManagerUrl";
const urlInput = document.getElementById("url");
const savedMsg = document.getElementById("savedMsg");

chrome.storage.local.get([STORAGE_KEY], (res) => {
  if (res[STORAGE_KEY]) urlInput.value = res[STORAGE_KEY];
});

document.getElementById("save").addEventListener("click", () => {
  const value = urlInput.value.trim();
  chrome.storage.local.set({ [STORAGE_KEY]: value }, () => {
    savedMsg.style.display = "block";
    setTimeout(() => { savedMsg.style.display = "none"; }, 2000);
  });
});
