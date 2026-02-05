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
    .vote-panel { margin-top: 14px; display:flex; flex-wrap:wrap; align-items:center; gap:10px; }
    .vote-btn { border:1px solid var(--line); background: var(--bg-soft); color: var(--text); border-radius: 10px; padding: 10px 14px; cursor:pointer; font-weight:600; }
    .vote-btn.live:hover { border-color: var(--alive); }
    .vote-btn.die:hover { border-color: var(--dead); }
    .vote-note { color: var(--muted); font-size: 13px; min-height: 18px; }
    .timeline-note { color: var(--muted); font-size: 12px; margin-top: 10px; }
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

    <section class="card vote-panel">
      <button class="vote-btn live" id="vote-live" type="button">Vote live</button>
      <button class="vote-btn die" id="vote-die" type="button">Vote die</button>
      <div class="vote-note" id="vote-note">One vote per round per visitor.</div>
    </section>

    <div class="timeline-note" id="timeline-note">Showing latest meaningful updates.</div>
    <section class="timeline" id="timeline"></section>
  </main>

  <script>
    const fallbackBase = `${window.location.protocol}//${window.location.hostname}:8080`;

    async function fetchJson(path) {
      const primary = await fetch(path);
      if (primary.ok) {
        return primary.json();
      }
      if (window.location.port !== '8080') {
        const backup = await fetch(`${fallbackBase}${path}`);
        if (backup.ok) {
          return backup.json();
        }
      }
      throw new Error(`request failed for ${path}`);
    }

    async function castVote(direction) {
      const note = document.getElementById('vote-note');
      note.textContent = 'sending vote...';
      try {
        const response = await fetch('/api/public/vote', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({vote: direction})
        });
        const payload = await response.json();
        if (!response.ok) {
          note.textContent = payload.detail || 'vote failed';
          return;
        }
        note.textContent = `vote accepted: live ${payload.data.live} / die ${payload.data.die}`;
        await loadAll();
      } catch (_error) {
        note.textContent = 'vote failed (network)';
      }
    }

    function shouldHideLegacyNoise(item, latestBootId) {
      if (item.moment_type === 'boot' && item.id !== latestBootId) {
        return true;
      }
      const legacyPulse = item.title === 'Pulse update'
        && item.content.startsWith('Life ')
        && item.content.includes('Vote pressure live/die:');
      return legacyPulse;
    }

    async function loadAll() {
      try {
        const [statePayload, votePayload, fundPayload, momentsPayload] = await Promise.all([
          fetchJson('/api/public/state'),
          fetchJson('/api/public/vote-round'),
          fetchJson('/api/public/funding'),
          fetchJson('/api/public/timeline?limit=20')
        ]);
        const state = statePayload.data;
        const vote = votePayload.data;
        const funding = fundPayload.data;
        const moments = momentsPayload.data;

        const pulse = document.getElementById('pulse');
        pulse.textContent = state.is_alive ? 'alive pulse' : 'dead pulse';
        pulse.className = 'pill ' + (state.is_alive ? 'alive' : 'dead');

        document.getElementById('state').textContent = `${state.state} (life ${state.life_number})`;
        document.getElementById('intention').textContent = state.current_intention;
        document.getElementById('votes').textContent = `live ${vote.live} / die ${vote.die}`;
        document.getElementById('funding').textContent = `${funding.donations.length} tracked donations`;

        const voteLive = document.getElementById('vote-live');
        const voteDie = document.getElementById('vote-die');
        voteLive.disabled = !state.is_alive;
        voteDie.disabled = !state.is_alive;

        const root = document.getElementById('timeline');
        root.innerHTML = '';
        const latestBoot = moments.find((m) => m.moment_type === 'boot');
        const latestBootId = latestBoot ? latestBoot.id : -1;
        const visibleMoments = moments.filter((item) => !shouldHideLegacyNoise(item, latestBootId));
        const note = document.getElementById('timeline-note');
        note.textContent = visibleMoments.length < moments.length
          ? `Showing ${visibleMoments.length} updates (filtered ${moments.length - visibleMoments.length} legacy pulses).`
          : 'Showing latest meaningful updates.';

        for (const item of visibleMoments) {
          const node = document.createElement('article');
          node.className = 'item';
          node.innerHTML = `<div class=\"row\"><span>${item.moment_type}</span><span>${item.created_at}</span></div><h4>${item.title}</h4><p>${item.content}</p>`;
          root.appendChild(node);
        }
      } catch (_error) {
        document.getElementById('pulse').textContent = 'sync failed';
        document.getElementById('state').textContent = 'unreachable';
        document.getElementById('intention').textContent = 'unreachable';
      }
    }
    document.getElementById('vote-live').addEventListener('click', () => castVote('live'));
    document.getElementById('vote-die').addEventListener('click', () => castVote('die'));
    loadAll();
    setInterval(loadAll, 15000);
  </script>
</body>
</html>
    """
