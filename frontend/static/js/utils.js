// Utils
(function(){
  function escapeHtml(str) {
    return String(str).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  }
  function formatDate(dt) {
    try { return new Date(dt).toLocaleString(); } catch { return dt; }
  }
  function riskBadge(level) {
    // Match inline CSS in index.html: .risk-badge, .risk-low/.risk-medium/.risk-high
    const lvl = String(level || '').toLowerCase();
    const cls = `risk-badge risk-${lvl}`;
    return `<span class="${cls}">${lvl}</span>`;
  }
  window.SekouUtils = { escapeHtml, formatDate, riskBadge };
})();
