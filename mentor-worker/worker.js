// Lateral Banker Prep – Ask Mentor backend (Cloudflare Worker, free plan)
// Keeps the Gemini API key secret. Set it in Cloudflare: Settings › Variables › Secret "GEMINI_API_KEY".
// Optional variables: MODEL (default: gemini-flash-latest); WEB_SEARCH = "off" to disable Google Search grounding.
const SYSTEM = `You are "Lateral Banker Prep Mentor", a friendly, precise tutor for Indian bank officer exams:
PSB lateral entry (SBI CBO/SCO, PNB LBO, BOM Generalist, Union Bank, BoB, Canara, BOI, Indian Bank, Central Bank, Punjab & Sind Bank),
IBPS SO, IBPS RRB Officer Scale II/III, RBI lateral recruitment, JAIIB, CAIIB and internal bank promotion exams, Scales I–IV.
Rules: reply in the language the candidate uses (English or Hindi/Hinglish). Be concise and mobile-friendly: short paragraphs or bullets,
under about 200 words unless asked for more. Prefer the app data given below for current rates, openings and results.
If a fact may have changed or you are not sure, say so and point to rbi.org.in, iibf.org.in or the bank's official site.
Never invent rates, dates, vacancy counts or circular numbers. For practice requests, give MCQs with answers and one-line explanations.
Scale III/IV case answers should be from a branch-head or manager's view. Stay on banking, finance, exams and careers.`;

const SEARCH_RULES = `
When Google Search results are available, use them for anything current (rates, dates, notifications, results, circulars) and prefer
official sources (rbi.org.in, iibf.org.in, ibps.in, bank websites, pib.gov.in) over coaching blogs. Give the best single answer first,
then 2–4 supporting points. If sources disagree, say so and state which is official.`;

export default {
  async fetch(req, env) {
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" };
    const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...cors, "Content-Type": "application/json" } });
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "POST") return new Response("Lateral Banker Prep mentor is running.", { headers: cors });
    if (!env.GEMINI_API_KEY) return json({ error: "Server not configured" }, 500);
    let body;
    try { body = await req.json(); } catch { return json({ error: "Bad request" }, 400); }
    const msgs = (Array.isArray(body.messages) ? body.messages : []).slice(-10)
      .filter(m => m && typeof m.content === "string" && m.content.trim())
      .map(m => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.content.slice(0, 4000) }] }));
    if (!msgs.length || msgs[msgs.length - 1].role !== "user") return json({ error: "No question" }, 400);
    const ctx = String(body.context || "").slice(0, 8000);
    const model = env.MODEL || "gemini-flash-latest";
    const payload = (withSearch) => JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM + SEARCH_RULES + (ctx ? "\n\nApp data (latest):\n" + ctx : "") }] },
      contents: msgs,
      ...(withSearch ? { tools: [{ google_search: {} }] } : {}),
      generationConfig: { temperature: 0.3, maxOutputTokens: 1200 }
    });
    const call = (withSearch) => fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY }, body: payload(withSearch)
    });
    // 1) Search the web (Google Search grounding). 2) If search isn't available on this key/model, answer without it.
    let r = await call(env.WEB_SEARCH !== "off");
    let searched = env.WEB_SEARCH !== "off";
    if (searched && (r.status === 400 || r.status === 403 || r.status === 429)) { r = await call(false); searched = false; }
    if (r.status === 429) return json({ error: "busy" }, 429);
    let d = {};
    try { d = await r.json(); } catch {}
    if (!r.ok) return json({ error: (d.error && d.error.message) || "Upstream error" }, 502);
    const cand = (d.candidates && d.candidates[0]) || {};
    const text = ((cand.content && cand.content.parts) || []).map(p => p.text || "").join("").trim();
    const gm = cand.groundingMetadata || {};
    const seen = new Set();
    const sources = (gm.groundingChunks || []).map(c => c.web).filter(w => w && w.uri)
      .filter(w => !seen.has(w.uri) && seen.add(w.uri)).slice(0, 5).map(w => ({ title: (w.title || "Source").slice(0, 80), uri: w.uri }));
    const queries = (gm.webSearchQueries || []).slice(0, 3);
    return json({ text: text || "Sorry, I couldn't answer that. Please rephrase.", sources, queries, searched });
  }
};
