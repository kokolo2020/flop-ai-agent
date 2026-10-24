'use strict';
// Pure state derivation shared by the dashboard and Node tests. Imports are unsigned.
(function(root) {
  const schema = 'computepilot.miner-test.v12';
  const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
  function validate(r) {
    if (!r || r.schema !== schema || r.simulated !== false || r.flop_activity !== 'NOT_VERIFIED' ||
        r.mining_activation !== 'NOT_PERFORMED' || !['preflight','benchmark','monitor','dcgm','aiperf','bundle'].includes(r.kind) ||
        r.evidence !== (r.kind === 'aiperf' ? 'EXTERNAL_OBSERVATION_UNSIGNED' : 'LOCAL_OBSERVATION_UNSIGNED') ||
        !Number.isFinite(Date.parse(r.collected_at))) throw Error('Expected an unsigned V12 observation. Fixtures and FLOP activity claims are excluded.');
    if (r.kind === 'preflight' && (!r.host || !Array.isArray(r.gpus) || !r.probes)) throw Error('Incomplete preflight report');
    if (['benchmark','aiperf'].includes(r.kind) && (!Number.isInteger(r.successful) || !Number.isInteger(r.requested) || !Number.isInteger(r.failed) || r.requested <= 0 || r.successful < 0 || r.failed < 0 || r.successful + r.failed !== r.requested)) throw Error('Inconsistent request counts');
    if (r.kind === 'benchmark' && !Array.isArray(r.rows)) throw Error('Missing benchmark rows');
    if (r.kind === 'aiperf' && (!r.metrics || r.model_identity !== 'NOT_VERIFIED')) throw Error('Incomplete AIPerf import');
    if (r.kind === 'monitor' && (!Array.isArray(r.samples) || !Array.isArray(r.alerts))) throw Error('Incomplete monitoring report');
    if (r.kind === 'dcgm' && (!Array.isArray(r.gpus) || !Array.isArray(r.alerts))) throw Error('Incomplete DCGM report');
    if (r.kind === 'bundle' && (!Array.isArray(r.checks) || !r.checks.length || r.checks.length > 100 || !r.checks.every(c => c && typeof c.check === 'string' && /^[A-Za-z0-9_]{1,100}$/.test(c.check) && ['PASS','FAIL','MISSING'].includes(c.status)) || r.operator_release_verification !== 'NOT_PERFORMED' || r.network_identity !== 'NOT_VERIFIED' || r.operator_admission !== 'NOT_VERIFIED' || r.activation_gate !== 'BLOCKED')) throw Error('Expected a sanitized offline bundle check; admission claims are excluded.');
    return r;
  }
  function hardware(gpus, target) {
    const profiles = {'a40': [/^(NVIDIA )?A40$/i,44000], 'a100-40': [/^(NVIDIA )?A100(-SXM4|-PCIE)?-40GB$/i,37000], 'a100-80': [/^(NVIDIA )?A100(-SXM4|-PCIE)?-80GB$/i,74000]};
    const profile = profiles[target];
    return !!profile && gpus.length === 1 && profile[0].test(gpus[0].name) && positive(gpus[0]['memory.total']) && gpus[0]['memory.total'] >= profile[1];
  }
  function readiness(report, target = 'a40', now = Date.now()) {
    const step = (id, title, state, reason) => ({id, title, state, reason});
    const steps = [step('bundle','Operator bundle','BLOCKED','Waiting for the operator bundle and approved model/image pins. Import only a sanitized checker report; keep private files on the host.'),
      step('host','GPU VM and SSH','ACTION_NEEDED','Provisioning is on hold. Collect an authorized VM preflight when access is available.'),
      step('inference','Measured Qwen inference','BLOCKED','Needs the approved checkpoint, measured BF16 backend identity and benchmark.'),
      step('protocol','FLOP miner compatibility','BLOCKED','TOPLOC, expected chain identity, registration and calibration require separate evidence.'),
      step('activation','Mining activation','BLOCKED','Requires your explicit approval before signing, sponsorship, registration or worker startup.')];
    if (!report) return steps;
    const r = validate(report), age = now - Date.parse(r.collected_at);
    if (age > 300000 || age < -60000) {
      steps[1] = step('host','GPU VM and SSH','ACTION_NEEDED','Snapshot is stale or its clock is in the future. Recollect on the host; no readiness is carried forward.');
      return steps;
    }
    if (r.kind === 'bundle') {
      const ok = r.configuration_checks === 'PASS' && r.checks.every(c => c.status === 'PASS');
      steps[0] = step('bundle','Operator bundle','ACTION_NEEDED',ok ? 'Offline consistency checks pass against supplied pins. Official release verification, network identity and admission remain unverified.' : 'Bundle files, approved pins or private configuration are missing or inconsistent. Inspect the sanitized checks; keep all raw files on the host.');
    }
    if (r.kind === 'preflight') {
      const probes = ['nvidia_smi','docker_server','compose','docker_gpu'];
      const unreachable = probes.some(k => r.probes[k]?.status === 'TIMEOUT_OR_OS_ERROR');
      const ok = r.host.os === 'Linux' && ['x86_64','amd64'].includes(r.host.arch) && hardware(r.gpus,target) && probes.every(k => r.probes[k]?.status === 'PASS') && r.ssh_access === 'PASS';
      steps[1] = step('host','GPU VM and SSH',ok ? 'READY' : unreachable ? 'UNREACHABLE' : 'ACTION_NEEDED',ok ? 'Recent unsigned report passes host, container GPU and SSH checks for this target. FLOP compatibility remains unverified.' : unreachable ? 'A host probe timed out or could not run. Restore access and recollect.' : 'Target GPU, Linux amd64, Docker GPU visibility or verified SSH is missing. A provider listing does not establish readiness.');
    }
    if (r.kind === 'benchmark') {
      const rows = r.rows.filter(row => row.warmup === false);
      const ok = r.failed === 0 && r.successful === r.requested && rows.length === r.requested && rows.every(row => row.status === 'PASS' && positive(row.e2e_ms) && Number.isInteger(row.completion_tokens) && row.completion_tokens > 0) && r.model === 'Qwen/Qwen2.5-0.5B-Instruct' && r.precision === 'BF16' && r.model_identity === 'measured' && /^0x[0-9a-f]{64}$/i.test(r.model_hash) && /^0x[0-9a-f]{64}$/i.test(r.policy_hash);
      steps[2] = step('inference','Measured Qwen inference',ok ? 'READY' : 'ACTION_NEEDED',ok ? 'Recent unsigned benchmark reports measured identity and successful inference. This alone says nothing about TOPLOC or accepted work.' : 'Benchmark failed or lacks consistent measurements and backend identity.');
    }
    if (r.kind === 'aiperf') steps[2] = step('inference','Measured Qwen inference','ACTION_NEEDED','AIPerf metrics imported. Host, model, BF16 and policy identity are not authenticated by the export.');
    if (r.kind === 'monitor' && r.samples.some(s => s.backend_health === 'UNAVAILABLE')) steps[2] = step('inference','Measured Qwen inference','UNREACHABLE','Backend health could not be reached during monitoring. Restore access and recollect.');
    return steps;
  }
  const api = {validate, readiness, hardware};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MinerReadiness = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
