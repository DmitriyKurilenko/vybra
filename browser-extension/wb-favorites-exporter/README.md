# WB Favorites Exporter for Vybra

Chrome extension (Manifest V3) to collect Wildberries favorites and copy them in a format that can be pasted into Vybra bulk import.

## Features

- Collect currently visible favorites from `wildberries.ru/lk/favorites`
- Auto-scroll and collect more products
- Copy output in Vybra-compatible text format (`name + url`)
- Download collected data as `.txt` or `.json`

## Install (Developer Mode)

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select this folder:
   `browser-extension/wb-favorites-exporter`

## Usage

1. Open your Wildberries favorites page in browser.
2. Open extension popup.
3. Click `Auto-scroll Collect` (or `Collect Visible`).
4. Click `Copy for Vybra`.
5. In Vybra, open items page and use bulk import modal (`import-favorites-bulk`) and paste text.

## Output Format

The extension copies data like:

```text
Product name 1
https://www.wildberries.ru/catalog/123456789/detail.aspx

Product name 2
https://www.wildberries.ru/catalog/987654321/detail.aspx
```

This format is accepted by the current Vybra parser.
