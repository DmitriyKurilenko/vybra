const state = {
  items: []
};

const ui = {
  collectVisibleBtn: document.getElementById("collectVisibleBtn"),
  collectAutoBtn: document.getElementById("collectAutoBtn"),
  copyVybraBtn: document.getElementById("copyVybraBtn"),
  downloadTxtBtn: document.getElementById("downloadTxtBtn"),
  downloadJsonBtn: document.getElementById("downloadJsonBtn"),
  maxItemsInput: document.getElementById("maxItemsInput"),
  statusLine: document.getElementById("statusLine"),
  countLine: document.getElementById("countLine"),
  previewArea: document.getElementById("previewArea")
};

function setBusy(isBusy) {
  ui.collectVisibleBtn.disabled = isBusy;
  ui.collectAutoBtn.disabled = isBusy;
}

function setStatus(text, subtext = "") {
  ui.statusLine.textContent = text;
  ui.countLine.textContent = subtext;
}

function updateActionsState() {
  const hasItems = state.items.length > 0;
  ui.copyVybraBtn.disabled = !hasItems;
  ui.downloadTxtBtn.disabled = !hasItems;
  ui.downloadJsonBtn.disabled = !hasItems;
}

function formatForVybra(items) {
  return items
    .map((item) => {
      const name = (item.name || `Product ${item.articleCode}`).trim();
      return `${name}\n${item.url}`;
    })
    .join("\n\n");
}

function previewText(items, maxLines = 12) {
  const lines = [];
  items.slice(0, maxLines).forEach((item, idx) => {
    lines.push(`${idx + 1}. ${item.name || `Product ${item.articleCode}`}`);
    lines.push(`   ${item.url}`);
  });
  if (items.length > maxLines) {
    lines.push(`... and ${items.length - maxLines} more`);
  }
  return lines.join("\n");
}

function downloadFile(filename, mimeType, text) {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function getActiveTabId() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs || tabs.length === 0) throw new Error("No active tab found.");
  return tabs[0].id;
}

function sendCollectMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      const runtimeError = chrome.runtime.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }
      resolve(response);
    });
  });
}

async function collect(mode) {
  setBusy(true);
  setStatus("Collecting...", "Please keep the Wildberries tab open.");
  try {
    const tabId = await getActiveTabId();
    const maxItems = Math.max(1, Number(ui.maxItemsInput.value) || 400);
    const response = await sendCollectMessage(
      tabId,
      mode === "autoscroll"
        ? { type: "WB_COLLECT_AUTOSCROLL", maxItems }
        : { type: "WB_COLLECT_VISIBLE" }
    );

    if (!response || !response.ok) {
      throw new Error((response && response.error) || "No data returned from page.");
    }

    state.items = response.items || [];
    ui.previewArea.value = previewText(state.items);
    setStatus(
      response.mode === "autoscroll" ? "Done (auto-scroll)" : "Done (visible only)",
      `Collected: ${state.items.length}`
    );
    updateActionsState();
  } catch (error) {
    setStatus("Collection failed", error.message || String(error));
  } finally {
    setBusy(false);
  }
}

async function copyForVybra() {
  const text = formatForVybra(state.items);
  await navigator.clipboard.writeText(text);
  setStatus("Copied", `Copied ${state.items.length} items in Vybra format.`);
}

function downloadTxt() {
  const text = formatForVybra(state.items);
  downloadFile("wb-favorites-for-vybra.txt", "text/plain;charset=utf-8", text);
  setStatus("Saved", "TXT file downloaded.");
}

function downloadJson() {
  const json = JSON.stringify(state.items, null, 2);
  downloadFile("wb-favorites.json", "application/json;charset=utf-8", json);
  setStatus("Saved", "JSON file downloaded.");
}

ui.collectVisibleBtn.addEventListener("click", () => collect("visible"));
ui.collectAutoBtn.addEventListener("click", () => collect("autoscroll"));
ui.copyVybraBtn.addEventListener("click", () => {
  copyForVybra().catch((error) => setStatus("Copy failed", error.message || String(error)));
});
ui.downloadTxtBtn.addEventListener("click", downloadTxt);
ui.downloadJsonBtn.addEventListener("click", downloadJson);

updateActionsState();
