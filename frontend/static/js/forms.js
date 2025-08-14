// Forms and overlay handling
(function(){
  const $ = (id) => document.getElementById(id);

  function applyTemplate(name) {
    const templates = {
      adult_respiratory: { age: 78, sex: 'female', fever: true, cough: true, shortness_of_breath: true },
      adult_mild: { age: 30, sex: 'male', fever: false, cough: false, shortness_of_breath: false },
      pediatric_fever: { age: 5, sex: 'other', fever: true, cough: true, shortness_of_breath: false },
    };
    const t = templates[name];
    if (!t) return;
    $('age').value = t.age;
    $('sex').value = t.sex;
    $('fever').checked = t.fever;
    $('cough').checked = t.cough;
    $('sob').checked = t.shortness_of_breath;
    const result = $('result'); if (result) result.textContent = '';
  }

  function resetForm(){
    $('age').value = '';
    $('sex').value = 'male';
    $('fever').checked = false;
    $('cough').checked = false;
    $('sob').checked = false;
    const result = $('result'); if (result) result.textContent = '';
  }

  async function submitTriage(){
    const payload = {
      name: ($('name') && $('name').value) ? $('name').value.trim() : undefined,
      age: parseInt(($('age').value || '0'), 10),
      sex: $('sex').value,
      fever: $('fever').checked,
      cough: $('cough').checked,
      shortness_of_breath: $('sob').checked,
      antecedents: ($('antecedents') && $('antecedents').value) ? $('antecedents').value.trim() : undefined,
    };
    try {
      const data = await window.SekouAPI.postTriage(payload);
      showRiskOverlay(data);
      await loadPredictions();
      await window.SekouDashboard.refreshStats();
    } catch (e) {
      const msg = (e && e.message) ? e.message : 'Error';
      showRiskOverlay({ risk_level: 'low', created_at: '', id: 0, error: msg }, true);
    }
  }

  async function loadPredictions(){
    const body = $('predictions-body'); if (!body) return;
    body.innerHTML = `<tr><td colspan="4" class="muted">Loading…</td></tr>`;
    try {
      const data = await window.SekouAPI.getPredictions();
      if (!Array.isArray(data) || data.length === 0) {
        body.innerHTML = `<tr><td colspan="4" class="muted">No records yet.</td></tr>`;
        return;
      }
      const { escapeHtml, riskBadge } = window.SekouUtils;
      body.innerHTML = data.map(r => `
        <tr>
          <td>${r.id}</td>
          <td>${riskBadge(r.risk_level)}</td>
          <td><time datetime="${r.created_at}">${window.SekouUtils.formatDate(r.created_at)}</time></td>
          <td><code class="nowrap">${escapeHtml(JSON.stringify(r.input_data))}</code></td>
        </tr>`).join('');
    } catch (e) {
      body.innerHTML = `<tr><td colspan="4" class="error">Failed to load: ${e}</td></tr>`;
    }
  }

  function showRiskOverlay(data, isError=false){
    const overlay = $('risk-overlay');
    const body = $('overlay-body');
    const badge = window.SekouUtils.riskBadge(data.risk_level || 'low');
    const extra = isError ? `<p class="error">${window.SekouUtils.escapeHtml(data.error || 'Submission failed')}</p>` : '';
    body.innerHTML = `${extra}<p>Risk level: ${badge}</p><p><small>id=${data.id} • ${data.created_at || ''}</small></p>`;
    overlay.classList.add('show');
    overlay.setAttribute('aria-hidden', 'false');
  }

  function hideRiskOverlay(){
    const overlay = $('risk-overlay');
    overlay.classList.remove('show');
    overlay.setAttribute('aria-hidden', 'true');
  }

  function wireUp(){
    document.querySelectorAll('[data-template]').forEach(btn => {
      btn.addEventListener('click', () => applyTemplate(btn.getAttribute('data-template')));
    });
    const btnPredict = $('btn-adult-predict'); if (btnPredict) btnPredict.addEventListener('click', submitTriage);
    const btnPeds = $('btn-peds-predict'); if (btnPeds) btnPeds.addEventListener('click', submitTriage);
    const btnReset = $('btn-reset'); if (btnReset) btnReset.addEventListener('click', resetForm);
    const btnLegacy = $('btn-legacy'); if (btnLegacy) btnLegacy.addEventListener('click', async () => {
      const data = await window.SekouAPI.postLegacy({ amount: 1500, category: 'general', features: { source: 'legacy-ui' } });
      $('legacy-result').textContent = JSON.stringify(data, null, 2);
    });
    const btnClose = $('overlay-close'); if (btnClose) btnClose.addEventListener('click', hideRiskOverlay);
    const overlay = $('risk-overlay'); if (overlay) overlay.addEventListener('click', (e) => { if (e.target === overlay) hideRiskOverlay(); });
  }

  window.SekouForms = { wireUp, applyTemplate, resetForm, submitTriage, loadPredictions };
})();
