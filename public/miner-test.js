'use strict';
(() => {
  const el = id => document.getElementById(id);
  let currentReport = null, stepIndex = 0;
  const guide = [
    ['1 / 5 · Validate operator inputs','Your access request is pending and renting remains on hold. Once the bundle arrives, keep it on the authorized host. Fill the preparation manifest with separately confirmed operator pins, then run the offline checker there. Import only its sanitized report. A consistency pass does not establish release authenticity or network admission.','python3 -m computepilot.operator_bundle --directory /opt/flop-miner --expected-manifest-sha256 OPERATOR_CONFIRMED_SHA256 --env miner-01.env --out miner-results/bundle-check.json'],
    ['2 / 5 · Verify the authorized VM','Use a full Linux amd64 VM with Docker, Compose, NVIDIA driver and Container Toolkit. Confirm the SSH host fingerprint independently and configure an SSH alias. Replace both placeholders below after access is authorized; the diagnostic image must be approved and digest-pinned.','python3 -m computepilot.miner_test ssh-preflight --host AUTHORIZED_ALIAS --target TARGET --cuda-image APPROVED_IMAGE@sha256:DIGEST --out miner-results/vm-preflight.json'],
    ['3 / 5 · Pin the model and backend','On the authorized VM, download the exact operator-approved Qwen revision. Use the matching operator backend and BF16 policy; confirm its measured model hash and policy hash. Backend startup requires VM authorization. Starting the miner worker also signs operations and requires separate approval.','bash scripts/download-qwen.sh --authorized-vm APPROVED_40_HEX_REV /opt/flop-miner/models/qwen-fresh'],
    ['4 / 5 · Measure inference and telemetry','Run the bounded benchmark inside the backend environment where its existing INFERENCE_API_KEY is available. It checks backend identity before requests. Collect DCGM only if an approved exporter is already installed and bound to loopback. AIPerf export imports provide optional timing detail; they do not prove model identity.','python3 -m computepilot.miner_test benchmark --model-hash OPERATOR_MODEL_HASH --policy-hash OPERATOR_POLICY_HASH --out miner-results/benchmark.json\npython3 -m computepilot.integrations dcgm --out miner-results/dcgm.json'],
    ['5 / 5 · Review before activation','Review measured inference separately from TOPLOC, registration, calibration and accepted work. Read current runtime constants before any stake commitment. Sponsorship, registration, signing, paid services and worker activation require your explicit approval. Offline wire checks exercise synthetic official vectors only.','python3 -m computepilot.wire_check']
  ];
  function showGuide() {
    const [title,text,command] = guide[stepIndex];
    el('stepTitle').textContent = title; el('stepText').textContent = text;
    el('stepCommand').textContent = command.replace('TARGET', el('target').value);
    el('previous').disabled = stepIndex === 0; el('next').disabled = stepIndex === guide.length - 1;
  }
  function showReadiness() {
    el('readiness').replaceChildren();
    for (const stage of MinerReadiness.readiness(currentReport, el('target').value)) {
      const block = document.createElement('p'), strong = document.createElement('strong'), detail = document.createElement('span');
      strong.textContent = `${stage.title} · ${stage.state.replaceAll('_',' ')}`;
      detail.textContent = stage.reason; detail.className = 'muted';
      block.append(strong, document.createElement('br'), detail); el('readiness').append(block);
    }
    showGuide();
  }
  el('target').onchange = showReadiness;
  el('previous').onclick = () => { stepIndex = Math.max(0,stepIndex-1); showGuide(); };
  el('next').onclick = () => { stepIndex = Math.min(guide.length-1,stepIndex+1); showGuide(); };
  function reset() {
    el('host').textContent = 'Not measured';
    el('inference').textContent = 'Not measured';
    el('metrics').replaceChildren(); el('telemetry').textContent = '';
  }
  function metric(name, value) {
    const row = document.createElement('tr');
    for (const [tag, text] of [['th', name], ['td', value ?? 'Unavailable']]) {
      const cell = document.createElement(tag); cell.textContent = String(text); row.append(cell);
    }
    el('metrics').append(row);
  }
  el('clear').onclick = () => { reset(); currentReport = null; showReadiness(); el('reportFile').value = ''; el('message').textContent = 'Report cleared.'; };
  el('reportFile').onchange = async () => {
    reset();
    try {
      const f = el('reportFile').files[0]; if (!f) return;
      if (f.size > 2_000_000) throw Error('Report exceeds 2 MB');
      const r = MinerReadiness.validate(JSON.parse(await f.text()));
      currentReport = r; showReadiness();
      const age = Date.now() - Date.parse(r.collected_at);
      el('message').textContent = 'IMPORTED · UNSIGNED · ' + (age > 300000 ? 'Snapshot older than five minutes.' : age < -60000 ? 'Timestamp is in the future; check host clock.' : 'Recent snapshot; not a live connection.');
      metric('Report', r.kind); metric('Collected at (UTC)', r.collected_at);
      if (r.kind === 'preflight') {
        el('host').textContent = r.host_prerequisites === 'PASS' ? 'Reported pass · unsigned' : 'Incomplete';
        metric('Host', `${r.host.os} / ${r.host.arch}`);
        metric('SSH access', r.ssh_access); metric('Report GPU target', r.target_gpu || 'a40'); metric('Hardware', r.target_hardware || r.target_a40_hardware);
        for (const key of ['nvidia_smi','docker_server','compose','docker_gpu']) metric(key, r.probes[key]?.status);
        el('telemetry').textContent = JSON.stringify(r.gpus.map(g => ({name:g.name, vram_mib:g['memory.total'], used_mib:g['memory.used'], utilization_pct:g['utilization.gpu'], temperature_c:g['temperature.gpu'], power_w:g['power.draw']})), null, 2);
      } else if (r.kind === 'bundle') {
        metric('Offline configuration', r.configuration_checks); metric('Scope', r.scope);
        for (const c of r.checks) metric(c.check,c.status);
        metric('Official release verification', r.operator_release_verification);
        metric('Network identity', r.network_identity); metric('Operator admission', r.operator_admission);
        metric('Activation', r.activation_gate);
      } else if (r.kind === 'benchmark') {
        el('inference').textContent = `${r.successful} / ${r.requested} reported successful`;
        for (const key of ['model','precision','median_e2e_ms','p95_e2e_ms','output_tokens_per_e2e_second','throughput_scope']) metric(key, r[key]);
      } else if (r.kind === 'monitor') {
        metric('Monitoring samples', r.samples.length);
        metric('Alerts', r.alerts.join(', ') || 'None reported');
        const last = r.samples.at(-1);
        metric('Last sample', last?.collected_at); metric('Backend health', last?.backend_health);
      } else if (r.kind === 'dcgm') {
        metric('DCGM GPU count', r.gpus.length); metric('Alerts', r.alerts.join(', ') || 'None reported');
        metric('Scope', r.scope);
        el('telemetry').textContent = JSON.stringify(r.gpus.map(g => Object.fromEntries(['gpu_index','temperature_c','power_w','utilization_pct','memory_used_mib','memory_free_mib','last_xid_error'].map(k => [k,g[k] ?? null]))), null, 2);
      } else if (r.kind === 'aiperf') {
        el('inference').textContent = `${r.successful} / ${r.requested} imported · identity unverified`;
        metric('Scope', r.scope); metric('Source SHA-256', r.source_sha256);
        for (const name of ['time_to_first_token','request_latency','inter_token_latency','output_token_throughput_per_user']) {
          const m = r.metrics[name]; metric(name, m?.samples ? `median ${m.median} · p95 ${m.p95} ${m.unit} (${m.samples} samples)` : 'Unavailable');
        }
      }
      for (const stage of ['TOPLOC','Registration','Calibration','Accepted FLOP work','Settlement']) metric(stage, 'NOT VERIFIED');
    } catch (e) { reset(); currentReport = null; showReadiness(); el('message').textContent = e instanceof SyntaxError ? 'Invalid JSON report.' : e.message; }
  };
  showReadiness();
  // A report cannot remain ready indefinitely while a tab is left open.
  setInterval(showReadiness, 30000);
})();
