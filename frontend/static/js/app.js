// App initialization: navigation, initial loads
(function(){
  function initNav(){
    document.querySelectorAll('.nav-link').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-target');
        document.querySelectorAll('.nav-link').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const section = document.getElementById(target);
        if (section) section.classList.add('active');
        if (target === 'view-history') window.SekouForms.loadPredictions();
        if (target === 'view-dashboard') window.SekouDashboard.refreshStats();
      });
    });
  }

  async function boot(){
    initNav();
    window.SekouForms.wireUp();
    await window.SekouForms.loadPredictions();
    await window.SekouDashboard.refreshStats();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
