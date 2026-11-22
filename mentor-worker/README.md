# Ask Mentor backend (free Gemini via Cloudflare Worker)

1. Get a free Gemini API key: https://aistudio.google.com → Get API key → Create API key (no billing needed).
2. Create a free Cloudflare account: https://dash.cloudflare.com → Workers & Pages → Create → Create Worker → name it `lbp-mentor` → Deploy.
3. Edit code → replace everything with `worker.js` from this folder → Deploy.
4. Worker → Settings → Variables and Secrets → Add → Type: Secret, Name: `GEMINI_API_KEY`, Value: your key → Deploy.
5. Copy the worker URL (https://lbp-mentor.<your-subdomain>.workers.dev) into `data/config.json` as `mentorUrl`. Installed apps pick it up on next launch – no new APK needed.

Optional plain variables: `MODEL` (default `gemini-flash-latest`) and `WEB_SEARCH` = `off` to turn off Google Search grounding (on by default; answers then show sources).
Free-tier limits apply per Google project and are shared by all app users. Free-tier prompts may be used by Google to improve its products.
