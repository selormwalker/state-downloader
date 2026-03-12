// api/cobalt.js  — Vercel serverless function
// Acts as a CORS-safe proxy to a self-hosted or community cobalt instance.
// Deploy this project to Vercel, set COBALT_INSTANCE env var in Vercel dashboard,
// or it defaults to the fallback list below.

const INSTANCES = [
  // Add your own self-hosted cobalt instance URL here for best reliability.
  // Community instances — no auth, CORS enabled, Instagram + all platforms.
  // These are checked in order; the first one that responds is used.
  'https://cobalt.ggtyler.dev',
  'https://co.wuk.sh',
  'https://cobalt.freecreations.org',
  'https://cobalt-api.hyper.lol',
];

const PRIMARY = process.env.COBALT_INSTANCE || null;

export default async function handler(req, res) {
  // CORS headers — allow your Vercel domain to call this
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const body = req.body;
  if (!body || !body.url) {
    return res.status(400).json({ error: 'Missing URL in request body' });
  }

  const instanceList = PRIMARY ? [PRIMARY, ...INSTANCES] : INSTANCES;

  let lastError = null;

  for (const instance of instanceList) {
    try {
      const cobaltRes = await fetch(`${instance}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'StateDownloader/1.0 (https://github.com/statedownloader)',
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(15000),
      });

      if (!cobaltRes.ok) {
        lastError = `Instance ${instance} returned ${cobaltRes.status}`;
        continue;
      }

      const data = await cobaltRes.json();

      // Forward the cobalt response to the client, adding which instance was used
      return res.status(200).json({ ...data, _instance: instance });

    } catch (err) {
      lastError = `Instance ${instance} failed: ${err.message}`;
      continue;
    }
  }

  return res.status(502).json({
    status: 'error',
    error: {
      code: 'error.api.unreachable',
      context: lastError || 'All instances failed',
    },
  });
}
