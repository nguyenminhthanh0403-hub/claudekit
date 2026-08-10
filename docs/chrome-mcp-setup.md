# Claude in Chrome — MCP Setup Guide

**What it enables:** Browser automation from Claude Code CLI — navigate, click, type, read console logs, take screenshots, record GIFs, interact with any web app you're logged into.

---

## Requirements

- Google Chrome or Microsoft Edge (not Brave, Arc, or other Chromium)
- Claude Code ≥ 2.0.73
- Direct Anthropic plan (Pro, Max, Team, or Enterprise)
- NOT available via Amazon Bedrock, Google Vertex AI, or Microsoft Foundry

---

## Step 1 — Install the Chrome Extension

Install **Claude in Chrome** from the Chrome Web Store:

```
https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn
```

Minimum version: 1.0.36

---

## Step 2 — Launch Claude Code with Chrome

```bash
claude --chrome
```

On first launch, Claude Code automatically installs a native messaging host config file so Chrome and the CLI can communicate. **Restart Chrome after the first connection** to pick up the new configuration.

---

## Step 3 — Enable by Default (optional)

To skip `--chrome` every session:

1. Run `/chrome` inside any Claude Code session
2. Select "Enabled by default"

Note: enabling by default increases context usage since browser tools are always loaded.

---

## Verify It's Working

Inside a Claude Code session, run:

```
/mcp
```

You should see `claude-in-chrome` listed with status connected and ~18 browser tools available.

---

## What You Can Do

| Task | Example prompt |
|---|---|
| Navigate and read | "Go to localhost:3000 and tell me what's on the page" |
| Test form validation | "Submit the login form with invalid data and check the error messages" |
| Read console logs | "Open the dashboard and check for JS errors in the console" |
| Interact with Google Docs | "Open my doc at [url] and add a summary of recent commits" |
| Extract data | "Go to [url] and save all product names and prices to products.csv" |
| Record a GIF | "Record a GIF of the checkout flow from cart to confirmation" |
| Multi-site workflow | "Check my calendar, then look up each attendee's company website" |

---

## Troubleshooting

**"Browser extension is not connected"**
→ Restart Chrome and Claude Code, then run `/chrome` → "Reconnect extension"

**Extension not detected**
→ Check `chrome://extensions` — extension must be enabled  
→ Restart Chrome to pick up the native messaging host config

**Native messaging host config location (macOS / Chrome):**
```
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json
```

**Connection drops during long sessions**
→ The extension's service worker can go idle. Run `/chrome` → "Reconnect extension"

**Windows — named pipe conflicts**
→ Restart Claude Code and close any other Claude Code sessions

---

## Security Notes

- Claude opens new tabs for browser tasks — it doesn't hijack existing tabs
- Claude shares your browser's login state (can access any site you're signed into)
- When it hits a login page or CAPTCHA, it pauses and asks you to handle it
- Site permissions are managed in the Chrome extension settings
