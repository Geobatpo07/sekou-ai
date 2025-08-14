// Dashboard logic: fetch predictions, compute stats, render charts
(function(){
  async function refreshStats() {
    const data = await window.SekouAPI.getPredictions().catch(() => []);
    const counts = { total: 0, low: 0, medium: 0, high: 0 };

    for (const r of data) {
      counts.total += 1;
      if (r.risk_level === 'low') counts.low += 1;
      else if (r.risk_level === 'medium') counts.medium += 1;
      else if (r.risk_level === 'high') counts.high += 1;
    }

    setText('stat-total', counts.total);
    setText('stat-low', counts.low);
    setText('stat-medium', counts.medium);
    setText('stat-high', counts.high);

    renderBarChart('risk-chart', [counts.low, counts.medium, counts.high]);
    renderPieChart(counts);
    renderComorbidList(extractTopComorbidities(data, 3));
  }

  function setText(id, val){
    const el = document.getElementById(id);
    if (el) el.textContent = String(val);
  }

  // Canvas bar chart (low, medium, high)
  function renderBarChart(canvasId, values) {
    const c = document.getElementById(canvasId);
    if (!c) return;
    const ctx = c.getContext('2d');
    const w = c.width = c.clientWidth || 600;
    const h = c.height = c.height || 140;
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(1, ...values);
    const labels = ['Low', 'Medium', 'High'];
    const colors = ['#10b981', '#f59e0b', '#ef4444'];
    const barW = Math.min(120, Math.floor((w - 60) / values.length));
    const gap = Math.floor((w - values.length * barW) / (values.length + 1));

    ctx.font = '12px system-ui, sans-serif';
    for (let i = 0; i < values.length; i++) {
      const x = gap + i * (barW + gap);
      const hBar = Math.round((values[i] / max) * (h - 40));
      const y = h - 20 - hBar;
      ctx.fillStyle = colors[i];
      ctx.fillRect(x, y, barW, hBar);
      ctx.fillStyle = '#374151';
      ctx.fillText(labels[i], x, h - 6);
      ctx.fillText(String(values[i]), x + Math.floor(barW / 2) - 6, y - 4);
    }
  }

  // Plotly pie chart
  function renderPieChart(counts) {
    const data = [{
      values: [counts.low, counts.medium, counts.high],
      labels: ['Low', 'Medium', 'High'],
      type: 'pie',
      marker: {
        colors: ['#10b981', '#f59e0b', '#ef4444']
      },
      textinfo: 'label+percent',
      insidetextorientation: 'radial'
    }];
    const layout = {
      margin: { t: 40, l: 10, r: 10, b: 10 },
      showlegend: true,
      responsive: true
    };
    Plotly.newPlot('risk-pie-chart', data, layout, { displayModeBar: false });
  }

  // Comorbidities extraction
  function extractTopComorbidities(data, topN = 3) {
    const freq = {};
    for (const r of data) {
      const antecedents = r.input_data?.antecedents;
      if (antecedents) {
        antecedents
          .split(",")
          .map(s => s.trim().toLowerCase())
          .forEach(cond => {
            if (cond) freq[cond] = (freq[cond] || 0) + 1;
          });
      }
    }
    return Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, topN);
  }

  // Comorbidity badge list
  function renderComorbidList(list) {
    const el = document.getElementById("comorb-list");
    if (!el) return;
    if (list.length === 0) {
      el.innerHTML = `<li class="list-group-item text-muted">No comorbidities found.</li>`;
      return;
    }
    el.innerHTML = "";
    for (const [name, count] of list) {
      const item = `<li class="list-group-item d-flex justify-content-between align-items-center">
        ${name}
        <span class="badge bg-primary rounded-pill">${count}</span>
      </li>`;
      el.insertAdjacentHTML("beforeend", item);
    }
  }

  // Auto init
  window.SekouDashboard = { refreshStats };
  document.addEventListener("DOMContentLoaded", refreshStats);
})();
