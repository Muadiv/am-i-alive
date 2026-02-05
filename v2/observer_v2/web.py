from __future__ import annotations


def index_html() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Am I Alive v2</title>
  <style>
    :root {
      --bg: #0f1714;
      --bg-soft: #17221d;
      --card: #1f2d26;
      --line: #2f463a;
      --text: #e8f3ed;
      --muted: #9cb8aa;
      --alive: #58d08a;
      --dead: #e76b6b;
      --warn: #f2b75e;
    }
    body { margin:0; font-family: "IBM Plex Sans", "Segoe UI", sans-serif; background: radial-gradient(circle at 20% 0%, #1f3028 0%, var(--bg) 55%); color:var(--text); }
    .wrap { max-width: 980px; margin: 0 auto; padding: 24px; }
    .hero { display:flex; flex-wrap:wrap; gap:12px; justify-content:space-between; align-items:center; margin-bottom: 16px; }
    .title { font-size: 28px; font-weight: 700; letter-spacing: 0.3px; }
    .pill { padding: 6px 12px; border:1px solid var(--line); background: var(--bg-soft); border-radius: 999px; font-size: 13px; color: var(--muted); }
    .grid { display:grid; gap:12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .card { background: linear-gradient(180deg, #213129 0%, var(--card) 100%); border:1px solid var(--line); border-radius: 14px; padding: 14px; }
    .k { color:var(--muted); font-size:12px; text-transform: uppercase; letter-spacing: 1px; }
    .v { margin-top:6px; font-size:18px; font-weight: 600; }
    .timeline { margin-top: 16px; display:flex; flex-direction:column; gap: 10px; }
    .item { border:1px solid var(--line); border-radius: 12px; padding: 12px; background: rgba(22,34,29,0.75); }
    .item h4 { margin:0 0 6px 0; font-size:15px; }
    .item p { margin:0; color:var(--muted); }
    .row { display:flex; justify-content:space-between; gap:10px; font-size:12px; color:var(--muted); margin-bottom:6px; }
    .alive { color:var(--alive); }
    .dead { color:var(--dead); }
    .warn { color:var(--warn); }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="title">Am I Alive v2</div>
      <div class="pill" id="pulse">syncing...</div>
    </section>

    <section class="grid">
      <article class="card"><div class="k">State</div><div class="v" id="state">-</div></article>
      <article class="card"><div class="k">Intention</div><div class="v" id="intention">-</div></article>
      <article class="card"><div class="k">Vote Round</div><div class="v" id="votes">-</div></article>
      <article class="card"><div class="k">Funding</div><div class="v" id="funding">-</div></article>
    </section>

    <section class="timeline" id="timeline"></section>
  </main>

  <script>
    async function loadAll() {
      const [stateRes, voteRes, fundRes, momentsRes] = await Promise.all([
        fetch('/api/public/state'),
        fetch('/api/public/vote-round'),
        fetch('/api/public/funding'),
        fetch('/api/public/timeline?limit=20')
      ]);
      const state = (await stateRes.json()).data;
      const vote = (await voteRes.json()).data;
      const funding = (await fundRes.json()).data;
      const moments = (await momentsRes.json()).data;

      const pulse = document.getElementById('pulse');
      pulse.textContent = state.is_alive ? 'alive pulse' : 'dead pulse';
      pulse.className = 'pill ' + (state.is_alive ? 'alive' : 'dead');

      document.getElementById('state').textContent = `${state.state} (life ${state.life_number})`;
      document.getElementById('intention').textContent = state.current_intention;
      document.getElementById('votes').textContent = `live ${vote.live} / die ${vote.die}`;
      document.getElementById('funding').textContent = `${funding.donations.length} tracked donations`;

      const root = document.getElementById('timeline');
      root.innerHTML = '';
      for (const item of moments) {
        const node = document.createElement('article');
        node.className = 'item';
        node.innerHTML = `<div class=\"row\"><span>${item.moment_type}</span><span>${item.created_at}</span></div><h4>${item.title}</h4><p>${item.content}</p>`;
        root.appendChild(node);
      }
    }
    loadAll();
    setInterval(loadAll, 15000);
  </script>
</body>
</html>
    """
