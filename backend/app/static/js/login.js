// Тёмная тема по умолчанию на странице логина.
// Если пользователь уже выбирал тему в админке — используем сохранённую.

(function loginTheme(){
  const root = document.documentElement;
  const body = document.body;
  const key = 'admin:theme';

  function apply(theme){
    root.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark');
    body.classList.toggle('light', theme === 'light');
    body.classList.toggle('dark', theme !== 'light');
  }

  function getInitial(){
    try {
      const saved = localStorage.getItem(key);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch(_) {}
    // По требованию — дефолтно тёмная на логине
    return 'dark';
  }

  function set(theme){
    try { localStorage.setItem(key, theme); } catch(_) {}
    apply(theme);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    apply(getInitial());

    const btn = document.getElementById('themeToggle');
    if(btn){
      btn.addEventListener('click', ()=>{
        const isDark = (root.getAttribute('data-theme') !== 'light') && body.classList.contains('dark');
        set(isDark ? 'light' : 'dark');
      });
    }
  });
})();
