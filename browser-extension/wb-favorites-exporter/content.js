(() => {
  const WB_HOST_RE = /(^|\.)wildberries\.ru$/i;
  const PRODUCT_URL_RE = /\/catalog\/(\d+)\/detail\.aspx/i;

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function isWbFavoritesPage() {
    const hostOk = WB_HOST_RE.test(window.location.hostname || "");
    const path = (window.location.pathname || "").toLowerCase();
    return hostOk && (path.includes("/lk/favorites") || path.includes("/favorites"));
  }

  function normalizeProductUrl(rawUrl) {
    if (!rawUrl) return null;
    try {
      const url = new URL(rawUrl, window.location.origin);
      const match = PRODUCT_URL_RE.exec(url.pathname || "");
      if (!match) return null;
      const articleCode = match[1];
      return {
        articleCode,
        url: `https://www.wildberries.ru/catalog/${articleCode}/detail.aspx`
      };
    } catch (e) {
      return null;
    }
  }

  function readProductName(cardEl) {
    const selectors = [
      ".product-card__name",
      ".product-card__title",
      "[class*='product-card__name']",
      "[class*='product-card__title']"
    ];
    for (const selector of selectors) {
      const node = cardEl.querySelector(selector);
      if (node && node.textContent && node.textContent.trim()) {
        return node.textContent.trim().replace(/\s+/g, " ");
      }
    }
    const fallback = cardEl.textContent ? cardEl.textContent.trim().split("\n")[0] : "";
    return fallback ? fallback.replace(/\s+/g, " ") : "";
  }

  function collectFromDom() {
    const map = new Map();
    const cardSelectors = [
      "article.product-card[data-nm-id]",
      "article[data-nm-id]",
      "div.product-card[data-nm-id]"
    ];
    const cardEls = document.querySelectorAll(cardSelectors.join(","));

    cardEls.forEach((cardEl) => {
      const dataId = (cardEl.getAttribute("data-nm-id") || "").trim();
      let normalized = null;

      if (dataId) {
        normalized = {
          articleCode: dataId,
          url: `https://www.wildberries.ru/catalog/${dataId}/detail.aspx`
        };
      } else {
        const a = cardEl.querySelector("a[href*='/catalog/'][href*='/detail.aspx']");
        normalized = normalizeProductUrl(a ? a.href : "");
      }

      if (!normalized) return;

      const name = readProductName(cardEl) || `Product ${normalized.articleCode}`;
      if (!map.has(normalized.articleCode)) {
        map.set(normalized.articleCode, {
          articleCode: normalized.articleCode,
          url: normalized.url,
          name
        });
      }
    });

    const linkEls = document.querySelectorAll("a[href*='/catalog/'][href*='/detail.aspx']");
    linkEls.forEach((a) => {
      const normalized = normalizeProductUrl(a.href || "");
      if (!normalized) return;
      if (!map.has(normalized.articleCode)) {
        const text = (a.textContent || "").trim().replace(/\s+/g, " ");
        map.set(normalized.articleCode, {
          articleCode: normalized.articleCode,
          url: normalized.url,
          name: text || `Product ${normalized.articleCode}`
        });
      }
    });

    return Array.from(map.values());
  }

  async function collectWithAutoScroll(maxItems = 300) {
    const target = Math.max(1, Number(maxItems) || 300);
    let best = collectFromDom();
    let stableRounds = 0;
    let previousCount = best.length;
    let previousHeight = document.body ? document.body.scrollHeight : 0;

    const maxRounds = 50;
    for (let i = 0; i < maxRounds; i += 1) {
      window.scrollTo(0, document.body.scrollHeight);
      await sleep(900 + Math.floor(Math.random() * 400));

      const loadMoreButton = Array.from(document.querySelectorAll("button")).find((btn) =>
        /show more|load more|показать/i.test((btn.textContent || "").trim())
      );
      if (loadMoreButton) {
        try {
          loadMoreButton.click();
          await sleep(700);
        } catch (e) {
          // no-op
        }
      }

      const current = collectFromDom();
      if (current.length > best.length) {
        best = current;
      }

      const currentHeight = document.body ? document.body.scrollHeight : previousHeight;
      const noGrowth = current.length === previousCount && currentHeight === previousHeight;
      if (noGrowth) {
        stableRounds += 1;
      } else {
        stableRounds = 0;
      }
      previousCount = current.length;
      previousHeight = currentHeight;

      if (best.length >= target) break;
      if (stableRounds >= 4) break;
    }

    return best;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || typeof message !== "object") return false;

    if (message.type === "WB_COLLECT_VISIBLE") {
      if (!isWbFavoritesPage()) {
        sendResponse({
          ok: false,
          error: "Open Wildberries favorites page first."
        });
        return false;
      }

      const items = collectFromDom();
      sendResponse({
        ok: true,
        mode: "visible",
        count: items.length,
        items
      });
      return false;
    }

    if (message.type === "WB_COLLECT_AUTOSCROLL") {
      if (!isWbFavoritesPage()) {
        sendResponse({
          ok: false,
          error: "Open Wildberries favorites page first."
        });
        return false;
      }

      collectWithAutoScroll(message.maxItems)
        .then((items) => {
          sendResponse({
            ok: true,
            mode: "autoscroll",
            count: items.length,
            items
          });
        })
        .catch((error) => {
          sendResponse({
            ok: false,
            error: `Failed to collect favorites: ${error && error.message ? error.message : String(error)}`
          });
        });
      return true;
    }

    return false;
  });
})();
