// аккуратное создание <img> для иконки
function makeIconImg(path){
  if (typeof path !== 'string' || !path.trim()) return null;
  const img = document.createElement('img');
  img.src = path;                 // ожидаем /media/... или http(s)://...
  img.alt = '';
  img.className = 'btn-icon';
  img.width = 18; img.height = 18;
  // если не загрузилась — спрячем, чтобы не ломать разметку
  img.addEventListener('error', () => { img.style.display = 'none'; });
  return img;
}

// ===== КНОПКИ ГЛАВНОЙ (устойчивый рендер с иконкой) =====
let _buttonsBusy = false;
let _buttonsAbort = null;

function getButtonsWrap() {
  return document.querySelector('#view > section[data-route="buttons"] #buttons');
}

async function fetchButtons(){
  if (_buttonsBusy) { try { _buttonsAbort?.abort(); } catch(e){} }
  _buttonsBusy = true;

  const wrap = getButtonsWrap();
  // если секция скрыта — покажем её (иначе визуально "пусто")
  const section = document.querySelector('#view > section[data-route="buttons"]');
  if (section) { section.hidden = false; section.removeAttribute('hidden'); }

  if (!wrap) { _buttonsBusy = false; return; }
  wrap.innerHTML = '<div class="muted">Загрузка…</div>';

  const ctrl = new AbortController();
  _buttonsAbort = ctrl;

  try {
    const res = await fetch('/home/buttons', { credentials:'same-origin', cache:'no-store', signal: ctrl.signal });
    const data = await res.json();

    wrap.innerHTML = '';
    if (!Array.isArray(data) || data.length === 0) {
      wrap.innerHTML = '<div class="muted">Кнопок пока нет</div>';
      return;
    }

    data.sort((a,b)=>(a.order_index ?? 0) - (b.order_index ?? 0));

    const frag = document.createDocumentFragment();
    for (const b of data){
      const item = document.createElement('div');
      item.className = 'btn-item';
      item.dataset.id = String(b.id);

      const title = document.createElement('div');
      title.className = 'btn-title';

      // иконка (необязательная)
      if (typeof b.icon_path === 'string' && b.icon_path.trim()){
        const iconImg = document.createElement('img');
        iconImg.className = 'btn-icon';
        iconImg.src = b.icon_path;
        iconImg.alt = '';
        iconImg.width = 18; iconImg.height = 18;
        iconImg.onerror = ()=> iconImg.remove();
        title.appendChild(iconImg);
      }

      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = `#${b.order_index ?? ''}`;
      title.appendChild(badge);

      title.insertAdjacentText('beforeend', ` ${b.title}`);

      const actions = document.createElement('div');
      actions.className = 'btn-actions';

      // если есть openBtnForm — добавим "Изменить"
      if (typeof openBtnForm === 'function'){
        const editBtn = makeIconBtn({ variant:'ghost', title:'Изменить', icon:ICONS.edit });
        editBtn.onclick = () => openBtnForm(b);
        actions.appendChild(editBtn);
      }

      const delBtn = makeIconBtn({ variant:'danger', title:'Удалить', icon:ICONS.trash });
      delBtn.onclick = async ()=>{
        if(!confirm('Удалить кнопку?')) return;
        await fetch(`/admin/buttons/${b.id}`, { method:'DELETE', credentials:'same-origin' });
        await fetchButtons();
      };
      actions.appendChild(delBtn);

      item.appendChild(title);
      item.appendChild(actions);
      frag.appendChild(item);
    }
    wrap.appendChild(frag);

  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('fetchButtons error:', e);
      wrap.innerHTML = '<div class="muted">Не удалось загрузить кнопки</div>';
    }
  } finally {
    _buttonsBusy = false;
  }
}


// простой экранировщик на всякий
function escapeHtml(s=''){
  return s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[m]));
}

async function createButton(){
  const title = prompt('Название кнопки');
  const target_slug = prompt('Slug страницы (target)');
  if(!title || !target_slug) return;
  await fetch('/admin/buttons', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    credentials: 'same-origin',
    body: JSON.stringify({title, target_slug, order_index: 99})
  });
  fetchButtons();
}

// ========================= Pages / Blocks =========================
let currentPage = null;

// Quill editor state
let quill = null;
let editorModal = null;
let editContext = { mode: 'create', blockId: null }; // mode: create|edit
let pagesInited = false;

// Convert Quill alignment classes to inline styles for wider compatibility (e.g., kiosk)
function normalizeQuillHtml(html = ''){
  try{
    const wrap = document.createElement('div');
    wrap.innerHTML = html;
    const sel = wrap.querySelectorAll('.ql-align-center, .ql-align-right, .ql-align-justify, .ql-align-left');
    sel.forEach(el => {
      if (el.classList.contains('ql-align-center')) el.style.textAlign = 'center';
      if (el.classList.contains('ql-align-right'))  el.style.textAlign = 'right';
      if (el.classList.contains('ql-align-justify')) el.style.textAlign = 'justify';
      if (el.classList.contains('ql-align-left'))   el.style.textAlign = 'left';
    });
    return wrap.innerHTML;
  }catch(_){
    return html;
  }
}

function initQuill(){
  if(pagesInited) return; // инициализируем один раз для секции
  editorModal = document.getElementById('editorModal');
  const editorEl = document.getElementById('quillEditor');
  if(!editorModal || !editorEl) return;

  const toolbar = [
    [{'header':[1,2,3,false]}],
    ['bold','italic','underline','strike'],
    [{'list':'ordered'},{'list':'bullet'}],
    ['link','blockquote','code-block'],
    [{'align':[]}],
    ['clean']
  ];
  quill = typeof Quill !== "undefined" ? new Quill('#quillEditor', {
    theme: 'snow',
    modules: { toolbar }
  }) : null;

  const closeBtn  = document.getElementById('editorClose');
  const cancelBtn = document.getElementById('editorCancel');
  const saveBtn   = document.getElementById('editorSave');

  if(closeBtn)  closeBtn.onclick  = closeEditor;
  if(cancelBtn) cancelBtn.onclick = closeEditor;
  if(saveBtn)   saveBtn.onclick   = saveEditor;

  // Кнопки формы «Страницы»
  const createPageBtn = document.getElementById('createPage');
  const loadPageBtn   = document.getElementById('loadPage');
  const addBlockBtn   = document.getElementById('addBlock');

  if(createPageBtn) createPageBtn.onclick = createPage;
  if(loadPageBtn)   loadPageBtn.onclick   = async () => {
    const slug = (document.getElementById('loadPageSlug')?.value || '').trim();
    if(slug) await loadPageBySlug(slug);
  };
  if(addBlockBtn)   addBlockBtn.onclick   = addBlock;

  pagesInited = true;
}

function openEditor({ title='Новый текстовый блок', html='', mode='create', blockId=null }){
  editContext = { mode, blockId };
  const titleEl = document.getElementById('editorTitle');
  if(titleEl) titleEl.textContent = title;
  if(quill){
    quill.setContents([]);
    if(html) quill.clipboard.dangerouslyPasteHTML(html);
  }
  if(editorModal){
    editorModal.classList.add('open');
    editorModal.setAttribute('aria-hidden','false');
  }
}

function closeEditor(){
  if(editorModal){
    editorModal.classList.remove('open');
    editorModal.setAttribute('aria-hidden','true');
  }
}

async function saveEditor(){
  if(!currentPage){ alert('Сначала загрузите страницу'); return; }
  const raw = (quill ? quill.root.innerHTML.trim() : '');
  const html = normalizeQuillHtml(raw);
  if(editContext.mode === 'edit' && editContext.blockId){
    await fetch(`/admin/blocks/${editContext.blockId}`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body: JSON.stringify({ kind:'text', content:{ html } })
    });
  } else {
    await fetch('/admin/blocks', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body: JSON.stringify({ page_id: currentPage.id, kind:'text', content:{ html } })
    });
  }
  closeEditor();
  await loadPage();
}

async function createPage(){
  const slug = (document.getElementById('pageSlug')?.value || '').trim();
  const title = (document.getElementById('pageTitle')?.value || '').trim();
  const is_home = !!document.getElementById('pageIsHome')?.checked;
  if(!slug || !title) return alert('Нужны slug и title');
  const res = await fetch('/admin/pages', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    credentials:'same-origin',
    body: JSON.stringify({slug, title, is_home})
  });
  if(res.status === 409){
    await loadPageBySlug(slug);
    return;
  }
  const page = await res.json();
  currentPage = page;
  renderPage(page);
}

async function loadPage(){
  if(!currentPage) return;
  await loadPageBySlug(currentPage.slug);
}

async function loadPageBySlug(slug){
  const res = await fetch(`/pages/${slug}`, { credentials:'same-origin' });
  if(!res.ok) return alert('Страница не найдена');
  const page = await res.json();
  currentPage = page;
  renderPage(page);
}

function renderPage(page){
  const info = document.getElementById('pageInfo');
  const list = document.getElementById('blocks');
  if(info) info.innerHTML = `Страница: <strong>${page.title}</strong> (<code>${page.slug}</code>) — блоков: ${page.blocks.length}`;
  if(!list) return;

  list.innerHTML = '';
  (page.blocks || []).forEach(blk => {
    const card = document.createElement('div');
    card.className = 'block-card';

    const head = document.createElement('div');
    head.className = 'block-head';

    // Значок и тип
    const left = document.createElement('div');
    left.className = 'kind-badge';
    const kicon = document.createElement('div');
    kicon.className = 'k';
    kicon.innerHTML = ICONS[blk.kind] || ICONS.text;
    const ktext = document.createElement('div');
    ktext.textContent = blk.kind.toUpperCase();
    left.appendChild(kicon);
    left.appendChild(ktext);

    // Actions
    const actions = document.createElement('div');
    actions.className = 'block-actions';

    const editBtn = makeIconBtn({ variant:'ghost', title:'Изменить', icon:ICONS.edit });
    editBtn.onclick = ()=> openBlockModal({ mode:'edit', block: blk });

    const delBtn = makeIconBtn({ variant:'danger', title:'Удалить', icon:ICONS.trash });
    delBtn.onclick = async ()=>{
      if(!confirm('Удалить блок?')) return;
      await fetch(`/admin/blocks/${blk.id}`, { method:'DELETE', credentials:'same-origin' });
      await loadPage();
      showToast?.({ title:'Удалено' });
    };

    actions.appendChild(editBtn);
    actions.appendChild(delBtn);

    head.appendChild(left);
    head.appendChild(actions);

    // Тело/мета
    const meta = document.createElement('div');
    meta.className = 'block-meta';

    if(blk.kind === 'text'){
      const snippet = (blk.content?.html || '').replace(/<[^>]+>/g,'').trim().slice(0,160);
      meta.textContent = snippet ? snippet + (snippet.length === 160 ? '…' : '') : 'Пустой текст';
    } else {
      meta.textContent = blk.content?.path || 'Путь не задан';
    }

    card.appendChild(head);
    card.appendChild(meta);
    list.appendChild(card);
  });
}

async function addBlock(){
  if(!currentPage) return alert('Сначала загрузите/создайте страницу');
  const kindSel = document.getElementById('newBlockKind');
  const valInp  = document.getElementById('newBlockValue');
  const kind = kindSel ? kindSel.value : 'text';
  const val  = (valInp ? valInp.value : '').trim();

  if(kind === 'text'){
    openEditor({ title:'Новый текстовый блок', html:'', mode:'create' });
    return;
  }
  if(!val) return;
  const content = (kind==='text') ? {html: val} : {path: val};
  await fetch('/admin/blocks', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    credentials:'same-origin',
    body: JSON.stringify({page_id: currentPage.id, kind, content})
  });
  await loadPage();
}

// ===== SVG icons
const ICONS = {
  pick:  `<svg viewBox="0 0 24 24"><path d="M12 5v14m7-7H5"/></svg>`, // плюс
  edit:  `<svg viewBox="0 0 24 24"><path d="M4 20h4l10-10a2.8 2.8 0 0 0-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/></svg>`,
  home:  `<svg viewBox="0 0 24 24"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>`,
  trash: `<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/></svg>`,
  text  : `<svg viewBox="0 0 24 24"><path d="M4 6h16M8 12h8M6 18h12"/></svg>`,
  image : `<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4z"/><path d="M7 14l3-3 3 3 4-4 2 2"/></svg>`,
  video : `<svg viewBox="0 0 24 24"><path d="M4 6h12v12H4z"/><path d="M16 10l4-2v8l-4-2z"/></svg>`,
  pdf : `<svg viewBox="0 0 24 24"><path d="M6 3h9l5 5v13H6z"/><path d="M15 3v5h5"/></svg>`
};

// factory
function makeIconBtn({variant='secondary', title='', icon=''}){
  const b = document.createElement('button');
  b.className = `iconbtn ${variant}`;
  b.innerHTML = icon;
  if(title) b.title = title;
  return b;
}


// ========================= Media Uploader =========================
let mediaInited = false;
let pickedFile = null;

function initMedia(){
  if(mediaInited) return;

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const pickBtn = document.getElementById('pickBtn');
  const uploadBtn = document.getElementById('uploadBtn');
  const mediaKindSel = document.getElementById('mediaKind');
  const preview = document.getElementById('preview');
  const thumb = document.getElementById('thumb');
  const uploadedPathEl = document.getElementById('uploadedPath');
  const externalUrl = document.getElementById('externalUrl');
  const addFromUrlBtn = document.getElementById('addFromUrl');

  const safe = (...els)=>els.every(Boolean);
  if(!safe(dropzone, fileInput, pickBtn, uploadBtn, mediaKindSel, preview, thumb, uploadedPathEl, externalUrl, addFromUrlBtn)) {
    return; // секция ещё не отрисована
  }

  // drag events
  ['dragenter','dragover'].forEach(ev=>{
    dropzone.addEventListener(ev, e=>{ e.preventDefault(); e.stopPropagation(); dropzone.classList.add('dragover'); });
  });
  ['dragleave','drop'].forEach(ev=>{
    dropzone.addEventListener(ev, e=>{ e.preventDefault(); e.stopPropagation(); dropzone.classList.remove('dragover'); });
  });
  dropzone.addEventListener('drop', (e)=>{
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if(!f) return;
    pickedFile = f;
    showPickedFile(f, preview, thumb, uploadedPathEl);
  });

  pickBtn.addEventListener('click', ()=> fileInput.click());
  fileInput.addEventListener('change', ()=>{
    pickedFile = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
    if(pickedFile) showPickedFile(pickedFile, preview, thumb, uploadedPathEl);
  });

  uploadBtn.addEventListener('click', async ()=>{
    try{
      if(!currentPage){ alert('Сначала загрузите/создайте страницу'); return; }
      if(!pickedFile){ alert('Выберите файл'); return; }
      const serverPath = await uploadFile(pickedFile);
      uploadedPathEl.textContent = serverPath;
      preview.hidden = false;
      const kind = mediaKindSel.value; // image | video | pdf
      await fetch('/admin/blocks', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ page_id: currentPage.id, kind, content: { path: serverPath } })
      });
      await loadPage();
    }catch(err){
      console.error(err);
      alert(err.message || 'Не удалось загрузить файл');
    }
  });

  addFromUrlBtn.addEventListener('click', async ()=>{
    try{
      if(!currentPage){ alert('Сначала загрузите/создайте страницу'); return; }
      const url = externalUrl.value.trim();
      if(!url) return;
      const kind = mediaKindSel.value;
      await fetch('/admin/blocks', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ page_id: currentPage.id, kind, content: { path: url } })
      });
      externalUrl.value = '';
      await loadPage();
    }catch(err){
      console.error(err);
      alert('Ошибка добавления по URL');
    }
  });

  mediaInited = true;
}

function showPickedFile(f, preview, thumb, uploadedPathEl){
  preview.hidden = false;
  uploadedPathEl.textContent = f.name;
  if(f.type.startsWith('image/')){
    const reader = new FileReader();
    reader.onload = e => {
      thumb.innerHTML = '';
      const img = document.createElement('img');
      img.src = e.target.result;
      Object.assign(img.style, { width:'56px', height:'56px', objectFit:'cover', borderRadius:'8px' });
      thumb.appendChild(img);
    };
    reader.readAsDataURL(f);
  } else if (f.type === 'application/pdf'){
    thumb.textContent = 'PDF';
  } else if (f.type.startsWith('video/')){
    thumb.textContent = 'VIDEO';
  } else {
    thumb.textContent = 'FILE';
  }
}

async function uploadFile(file){
  const fd = new FormData();
  fd.append('file', file, file.name);
  const res = await fetch('/upload', { method: 'POST', body: fd, credentials: 'same-origin' });
  if(!res.ok){
    const t = await res.text();
    throw new Error('Upload failed: ' + t);
  }
  const data = await res.json(); // { path: "/media/xxx.ext" }
  return data.path;
}

// ========================= Router =========================
function findSection(route){
  return (
    document.querySelector(`#view > section[data-route="${route}"]`) ||
    document.getElementById(`section-${route}`) ||
    document.querySelector(`[data-route="${route}"]`)
  );
}

const ROUTE_INITED = { dashboard:false, pages:false, buttons:false, media:false, theme:false };

function showSection(route){
  // скрыть все верхнеуровневые секции
  document.querySelectorAll('#view > section[data-route]').forEach(s => { s.hidden = true; });

  // показать нужную
  const sel = findSection(route);
  if (!sel) {
    console.warn('[router] section not found for:', route);
    return;
  }
  sel.hidden = false;            // важный момент — снимаем hidden
  sel.removeAttribute('hidden'); // на всякий случай, если атрибутом скрывали

  // заголовок
  const titles = { dashboard:'Админ-панель', pages:'Страницы', buttons:'Кнопки', media:'Медиа', theme:'Стили' };
  const h = document.getElementById('viewTitle');
  if (h) h.textContent = titles[route] || 'Админ-панель';

  // активное меню
  document.querySelectorAll('#sideNav .nav-item').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#/' + route);
  });

  // ленивые init
  if (route === 'buttons') {
    if (!ROUTE_INITED.buttons) {
      const createBtn = document.getElementById('createBtn');
      if (createBtn) createBtn.onclick = createButton;
      if (typeof initButtonsModal === 'function') initButtonsModal();
      if (typeof preloadPages === 'function' && typeof fillTargetSelect === 'function') {
        preloadPages().then(fillTargetSelect);
      }
      if (typeof preloadGroups === 'function' && typeof fillGroupSelect === 'function') {
        preloadGroups().then(fillGroupSelect);
      }
      ROUTE_INITED.buttons = true;
    }
    // каждый вход — перерисовка
    fetchButtons();
    if (typeof refreshGroupsList === 'function') refreshGroupsList();
  }

  if (route === 'dashboard') {
    if (!ROUTE_INITED.dashboard) {
      if (typeof initDashboard === 'function') initDashboard();
      ROUTE_INITED.dashboard = true;
    }
    if (typeof loadDashboard === 'function') loadDashboard();
  }

  if (route === 'pages') {
    if (!ROUTE_INITED.pages) {
      if (typeof initQuill === 'function') initQuill();
      if (typeof initPagesUI === 'function') initPagesUI();
      if (typeof initBlocksUI === 'function') initBlocksUI();
      ROUTE_INITED.pages = true;
    }
  }

  if (route === 'media') {
    if (!ROUTE_INITED.media) {
      if (typeof initMedia === 'function') initMedia();
      ROUTE_INITED.media = true;
    }
  }
}

function getRouteFromHash(){
  const h = window.location.hash || '#/dashboard';
  const route = h.replace(/^#\//,'');
  return route || 'dashboard';
}

function navigate(){
  const route = getRouteFromHash();
  try { localStorage.setItem('admin:lastRoute', route); } catch(e){}
  showSection(route);
}

window.addEventListener('hashchange', navigate);
document.addEventListener('DOMContentLoaded', () => {
  try {
    const saved = localStorage.getItem('admin:lastRoute');
    if (saved) window.location.hash = '#/' + saved;
    else if (!window.location.hash) window.location.hash = '#/dashboard';
  } catch(e) {
    if (!window.location.hash) window.location.hash = '#/dashboard';
  }
  navigate();
});

// ========================= Dashboard (Org + Logo) =========================
let orgInput, logoPick, logoUpload, logoFile, logoImg, orgSave;
let dashboardState = { logo_path: '' };

async function loadConfig(){
  try{
    const res = await fetch('/config', { credentials:'same-origin', cache:'no-store' });
    return await res.json();
  }catch(_){ return null }
}

function initDashboard(){
  orgInput   = document.getElementById('orgName');
  const exitPwd   = document.getElementById('exitPwd');
  logoPick   = document.getElementById('logoPick');
  logoUpload = document.getElementById('logoUpload');
  logoFile   = document.getElementById('logoFile');
  logoImg    = document.getElementById('logoImg');
  orgSave    = document.getElementById('orgSave');

  // Weather controls: city selector + visibility toggle
  try{
    const section = document.getElementById('section-dashboard');
    const orgPanel = section ? section.querySelector('.panel') : null;
    if (orgPanel && !orgPanel.querySelector('#weatherCitySelect')){
      const grid = document.createElement('div');
      grid.className = 'form-grid';
      grid.style.marginTop = '12px';
      grid.innerHTML = `
        <label class="field" style="max-width:360px;">
          <span>Город (Беларусь)</span>
          <select id="weatherCitySelect">
            <option value="">— Выберите город —</option>
            <option>Минск</option>
            <option>Брест</option>
            <option>Витебск</option>
            <option>Гомель</option>
            <option>Гродно</option>
            <option>Могилёв</option>
          </select>
        </label>
        <label class="field" style="align-items:center; max-width:260px;">
          <span>Отображать погоду</span>
          <input type="checkbox" id="weatherShow" />
        </label>`;
      const footer = orgPanel.querySelector('.footer');
      if (footer && footer.parentElement){
        footer.parentElement.insertBefore(grid, footer);
      } else {
        orgPanel.appendChild(grid);
      }
    }
  }catch(_){ }

  if (logoPick && logoFile){ logoPick.onclick = ()=> logoFile.click(); }
  if (logoUpload && logoFile){
    logoUpload.onclick = async ()=>{
      if (!logoFile.files || !logoFile.files[0]) return alert('Выберите файл логотипа');
      const path = await uploadFile(logoFile.files[0]);
      dashboardState.logo_path = path;
      if (logoImg){ logoImg.src = path; logoImg.hidden = false; }
      showToast?.({ title:'Логотип загружен', message: path });
    };
  }
  if (orgSave){
    orgSave.onclick = async ()=>{
      const org_name = (orgInput?.value || '').trim();
      const payload = { org_name };
      const pw = (exitPwd?.value || '').trim();
      if (pw) payload.kiosk_exit_password = pw;
      if (dashboardState.logo_path) payload.logo_path = dashboardState.logo_path;
      // Weather fields
      try{
        const wc = document.getElementById('weatherCitySelect');
        const sw = document.getElementById('weatherShow');
        if (sw) payload.show_weather = !!sw.checked;
        if (wc) payload.weather_city = (wc.value || '').trim();
      }catch(_){ }
      const res = await fetch('/admin/settings', {
        method:'PUT', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
        body: JSON.stringify(payload)
      });
      if (!res.ok){ const t = await res.text(); alert(t || 'Не удалось сохранить'); return; }
      showToast?.({ title:'Сохранено', type:'success' });
      if (exitPwd) exitPwd.value = '';
    };
  }

  // Модуль: киоск‑пароль (отдельный)
  const pwd1 = document.getElementById('kioskPwd1');
  const pwd2 = document.getElementById('kioskPwd2');
  const btnSave = document.getElementById('kioskPwdSave');
  const btnClear = document.getElementById('kioskPwdClear');
  const statusEl = document.getElementById('kioskPwdStatus');

  if (btnSave){
    btnSave.onclick = async ()=>{
      const a = (pwd1?.value || '').trim();
      const b = (pwd2?.value || '').trim();
      if (!a) return alert('Введите пароль');
      if (a !== b) return alert('Пароли не совпадают');
      const r = await fetch('/admin/kiosk/exit-password', {
        method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
        body: JSON.stringify({ password: a })
      });
      if(!r.ok){ alert('Не удалось сохранить'); return; }
      const j = await r.json();
      showToast?.({ title:'Сохранено', type:'success' });
      if (statusEl) statusEl.textContent = 'Статус: ' + (j.exit_password_set ? 'Установлен' : 'Не установлен');
      if(pwd1) pwd1.value=''; if(pwd2) pwd2.value='';
    };
  }
  if (btnClear){
    btnClear.onclick = async ()=>{
      if(!confirm('Сбросить пароль выхода?')) return;
      const r = await fetch('/admin/kiosk/exit-password', {
        method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
        body: JSON.stringify({ clear: true })
      });
      if(!r.ok){ alert('Не удалось сбросить'); return; }
      const j = await r.json();
      showToast?.({ title:'Сброшено', type:'success' });
      if (statusEl) statusEl.textContent = 'Статус: ' + (j.exit_password_set ? 'Установлен' : 'Не установлен');
    };
  }

  // Обновим статус модуля пароля из точного админского эндпоинта
  try{
    const statusEl = document.getElementById('kioskPwdStatus');
    if (statusEl){
      fetch('/admin/kiosk/exit-password/status', { credentials:'same-origin', cache:'no-store' })
        .then(r => r.ok ? r.json() : null)
        .then(j => { if (j) statusEl.textContent = 'Статус: ' + (j.exit_password_set ? 'Установлен' : 'Не установлен'); })
        .catch(() => {});
    }
  }catch(_){ }

}

async function loadDashboard(){
  const cfg = await loadConfig();
  if (!cfg) return;
  if (orgInput) orgInput.value = cfg.org_name || '';
  const lp = cfg.theme && cfg.theme.logo_path || '';
  dashboardState.logo_path = lp;
  if (logoImg){
    if (lp){ logoImg.src = lp; logoImg.hidden = false; }
    else { logoImg.hidden = true; }
  }
  // Weather: fill current values
  try{
    const citySel = document.getElementById('weatherCitySelect');
    const sw = document.getElementById('weatherShow');
    const city = cfg.weather_city || '';
    if (citySel){
      const found = Array.from(citySel.options).find(o => (o.value||o.text) === city);
      if (found) citySel.value = city;
    }
    if (sw) sw.checked = !!cfg.show_weather;
  }catch(_){ }
  try{ const st = document.getElementById('kioskPwdStatus'); if(st) st.textContent = 'Статус: ' + (cfg.exit_password_set ? 'Установлен' : 'Не установлен'); }catch(_){ }
  // Поверх значения из /config берём точный статус из админского эндпоинта (без кэша)
  try{
    fetch('/admin/kiosk/exit-password/status', { credentials:'same-origin', cache:'no-store' })
      .then(r => r.ok ? r.json() : null)
      .then(j => {
        if (!j) return;
        const st = document.getElementById('kioskPwdStatus');
        if (st) st.textContent = 'Статус: ' + (j.exit_password_set ? 'Установлен' : 'Не установлен');
      })
      .catch(()=>{});
  }catch(_){ }
}

// ========================= THEME (robust) =========================
(function themeManager(){
  const root = document.documentElement;
  const body = document.body;
  const key = 'admin:theme';

  function apply(theme){
    // два способа одновременно — для совместимости со старыми стилями
    root.setAttribute('data-theme', theme === 'dark' ? 'dark' : 'light');
    body.classList.toggle('dark', theme === 'dark');
  }

  function getInitial(){
    try {
      const saved = localStorage.getItem(key);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (_) {}
    // если сохранения нет — берём системную
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
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
        const isDark = root.getAttribute('data-theme') === 'dark' || body.classList.contains('dark');
        set(isDark ? 'light' : 'dark');
      });
    }
  });
})();

// ========================= TOASTS =========================
function showToast({title='Готово', message='', type='success', timeout=3000} = {}){
  const wrap = document.getElementById('toasts');
  if(!wrap) return;
  const el = document.createElement('div');
  el.className = 'toast ' + (type || '');
  el.innerHTML = `
    <div>
      <div class="title">${title}</div>
      ${message ? `<div class="body">${message}</div>` : ``}
    </div>
    <button class="close" aria-label="Close">×</button>
  `;
  el.querySelector('.close').onclick = () => wrap.removeChild(el);
  wrap.appendChild(el);
  if(timeout) setTimeout(()=>{ if(el.parentNode) wrap.removeChild(el); }, timeout);
}

// ========================= DnD: Buttons ordering =========================
function enableButtonsDnD(){
  const list = document.getElementById('buttons');
  if(!list) return;
  const items = Array.from(list.querySelectorAll('.btn-item'));
  items.forEach((it, idx) => {
    it.setAttribute('draggable', 'true');
    it.dataset.id = it.dataset.id || '';
    it.addEventListener('dragstart', onDragStart);
    it.addEventListener('dragover', onDragOver);
    it.addEventListener('drop', onDrop);
    it.addEventListener('dragend', onDragEnd);
  });

  let dragEl = null;
  function onDragStart(e){
    dragEl = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  }
  function onDragOver(e){
    e.preventDefault();
    const target = (e.currentTarget);
    if(!dragEl || dragEl === target) return;
    const rect = target.getBoundingClientRect();
    const before = (e.clientY - rect.top) < (rect.height / 2);
    target.parentNode.insertBefore(dragEl, before ? target : target.nextSibling);
  }
  function onDrop(e){ e.preventDefault(); }
  function onDragEnd(){
    this.classList.remove('dragging');
    saveButtonsOrder();
  }

  async function saveButtonsOrder(){
    const ordered = Array.from(list.querySelectorAll('.btn-item')).map((el, i) => ({
      id: parseInt(el.getAttribute('data-id'), 10),
      order_index: i + 1
    })).filter(x => !Number.isNaN(x.id));

    let ok = false;
    try{
      const res = await fetch('/admin/buttons/reorder', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ items: ordered })
      });
      ok = res.ok;
    } catch(_){ ok = false; }

    if(!ok){
      console.log('Новый порядок кнопок:', ordered);
      showToast({ title:'Перетаскивание', message:'Добавь эндпоинт POST /admin/buttons/reorder для сохранения порядка', type:'error', timeout:4000 });
    } else {
      showToast({ title:'Сохранено', message:'Порядок кнопок обновлён', type:'success' });
      fetchButtons();
    }
  }
}

// ===== ВСТАВКА ХУКОВ в существующие функции =====

// после fetchButtons() — добавим data-id и включим DnD
const _origFetchButtons = fetchButtons;
fetchButtons = async function(){
  await _origFetchButtons();
  const wrap = document.querySelector('#view > section[data-route="buttons"] #buttons');
  if(wrap){
    const buttons = await (await fetch('/home/buttons', { credentials: 'same-origin' })).json();
    const list = Array.isArray(buttons) ? buttons : [];
    Array.from(wrap.querySelectorAll('.btn-item')).forEach(item => {
      const text = item.querySelector('.btn-title')?.innerText || '';
      const match = list.find(b => text.includes(b.title));
      if(match) item.setAttribute('data-id', match.id);
    });
  }
  enableButtonsDnD();
};

// показываем тосты в существующих действиях
const _origCreateButton = createButton;
createButton = async function(){
  await _origCreateButton();
  showToast({ title:'Кнопка создана', type:'success' });
};

const _origAddBlock = addBlock;
addBlock = async function(){
  await _origAddBlock();
  showToast({ title:'Блок добавлен', type:'success' });
};

// ========================= Buttons Modal (Create/Edit) =========================
let btnModal, btnTitle, btnTarget, btnBg, btnFg, btnIconFile, btnPickIcon, btnUploadIcon, btnIconPath, btnSave, btnCancel, btnClose, btnPalette;
let btnEditingId = null; // null => create

const PALETTE = [
  "#2563eb","#1d4ed8","#0ea5e9","#22c55e","#16a34a","#f59e0b","#ef4444",
  "#f97316","#a855f7","#6b7280","#111827","#0ea5e9","#f43f5e","#10b981",
  "#eab308","#8b5cf6"
];

function initButtonsModal(){
  if (btnModal) return; // 1 раз
  btnModal      = document.getElementById('btnModal');
  btnTitle      = document.getElementById('btnTitle');
  btnTarget     = document.getElementById('btnTarget');
  btnBg         = document.getElementById('btnBg');
  btnFg         = document.getElementById('btnFg');
  btnIconFile   = document.getElementById('btnIconFile');
  btnPickIcon   = document.getElementById('btnPickIcon');
  btnUploadIcon = document.getElementById('btnUploadIcon');
  btnIconPath   = document.getElementById('btnIconPath');
  btnSave       = document.getElementById('btnSave');
  btnCancel     = document.getElementById('btnCancel');
  btnClose      = document.getElementById('btnClose');
  btnPalette    = document.getElementById('btnPalette');
  const btnGroupSel = document.getElementById('btnGroup');

  // Открыть пустую форму
  const openBtn = document.getElementById('openBtnModal');
  if (openBtn) openBtn.onclick = () => openBtnForm();

  // Кнопки modal
  if (btnCancel) btnCancel.onclick = closeBtnForm;
  if (btnClose)  btnClose.onclick  = closeBtnForm;
  if (btnSave)   btnSave.onclick   = saveBtnForm;

  // Иконка
  if (btnPickIcon) btnPickIcon.onclick = () => btnIconFile && btnIconFile.click();
  if (btnUploadIcon) btnUploadIcon.onclick = async () => {
    if (!btnIconFile || !btnIconFile.files || !btnIconFile.files[0]) {
      showToast?.({ title: 'Файл не выбран', type: 'error' });
      return;
    }
    const path = await uploadFile(btnIconFile.files[0]);
    btnIconPath.textContent = path;
    showToast?.({ title: 'Иконка загружена', message: path });
  };

  // Палитра
  if (btnPalette){
    btnPalette.innerHTML = '';
    PALETTE.forEach(color => {
      const sw = document.createElement('button');
      sw.type = 'button';
      sw.className = 'swatch';
      sw.style.background = color;
      sw.title = color;
      sw.addEventListener('click', ()=>{
        selectSwatch(sw);
        btnBg.value = color;
        const fgPref = (document.querySelector('input[name="fg"]:checked')?.value) || 'light';
        btnFg.value = fgPref === 'dark' ? '#111827' : '#ffffff';
      });
      btnPalette.appendChild(sw);
    });
  }

  // Переключатели текста (light/dark)
  document.querySelectorAll('input[name="fg"]').forEach(r=>{
    r.addEventListener('change', ()=>{
      btnFg.value = r.value === 'dark' ? '#111827' : '#ffffff';
    });
  });

  // Подгружаем страницы и группы в select'ы
  preloadPages().then(()=>fillTargetSelect());
  preloadGroups().then(()=>fillGroupSelect());

  // Создание группы по кнопке (простые prompt'ы)
  const createGroupBtn = document.getElementById('createGroupBtn');
  if (createGroupBtn) createGroupBtn.onclick = async ()=>{
    const title = (prompt('Название группы') || '').trim();
    if (!title) return;
    const res = await fetch('/admin/button-groups', {
      method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
      body: JSON.stringify({ title })
    });
    if (!res.ok){ const t = await res.text(); alert(t || 'Не удалось создать группу'); return; }
    await preloadGroups();
    fillGroupSelect();
    await refreshGroupsList();
    showToast?.({ title:'Группа создана', type:'success' });
  };
}

function selectSwatch(el){
  btnPalette.querySelectorAll('.swatch').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
}

async function preloadPages(){
  try{
    const res = await fetch('/admin/pages', { credentials: 'same-origin' });
    window.__pagesCache = await res.json();
  }catch(_){
    window.__pagesCache = [];
  }
}
function fillTargetSelect(selectedSlug){
  const btnTarget = document.getElementById('btnTarget');
  if (!btnTarget) return;
  btnTarget.innerHTML = '';
  const opt = document.createElement('option');
  opt.value = ''; opt.textContent = '— выберите страницу —';
  btnTarget.appendChild(opt);
  (window.__pagesCache || []).forEach(p => {
    const o = document.createElement('option');
    o.value = p.slug;
    o.textContent = `${p.title}`;
    if (selectedSlug && selectedSlug === p.slug) o.selected = true;
    btnTarget.appendChild(o);
  });
}

// ===== Button Groups: preload + select fill + list =====
async function preloadGroups(){
  try{
    const res = await fetch('/admin/button-groups', { credentials:'same-origin' });
    window.__groupsCache = await res.json();
  }catch(_){ window.__groupsCache = []; }
}
function fillGroupSelect(selectedId){
  const sel = document.getElementById('btnGroup');
  if (!sel) return;
  sel.innerHTML = '';
  const opt0 = document.createElement('option');
  opt0.value = ''; opt0.textContent = '— без группы —';
  sel.appendChild(opt0);
  (window.__groupsCache || []).forEach(g => {
    const o = document.createElement('option');
    o.value = String(g.id);
    o.textContent = g.title;
    if (selectedId && Number(selectedId) === g.id) o.selected = true;
    sel.appendChild(o);
  });
}
async function refreshGroupsList(){
  const list = document.getElementById('groupsList');
  if (!list) return;
  await preloadGroups();
  list.innerHTML = '';

  // Получим дерево меню, чтобы показать состав групп
  let menu = [];
  try { menu = await (await fetch('/home/menu', { credentials:'same-origin', cache:'no-store' })).json(); } catch(_) { menu = []; }
  const groupsById = Object.fromEntries((window.__groupsCache||[]).map(g => [g.id, g]));
  const itemsByGroup = {};
  menu.forEach(node => { if(node.kind==='group' && node.id!=null) itemsByGroup[node.id] = node.items || []; });

  (window.__groupsCache || []).forEach(g => {
    const el = document.createElement('div');
    el.className = 'item';

    const top = document.createElement('div'); top.className = 'top';
    const left = document.createElement('div');
    const t = document.createElement('div'); t.className = 'title'; t.textContent = g.title;
    const s = document.createElement('div'); s.className = 'slug'; s.textContent = `#${g.order_index ?? 0}`;
    left.appendChild(t); left.appendChild(s);

    const right = document.createElement('div'); right.className = 'actions';
    const edit = makeIconBtn({ variant:'ghost', title:'Переименовать', icon:ICONS.edit });
    edit.onclick = async ()=>{
      const nt = (prompt('Название группы', g.title) || '').trim();
      if (!nt) return;
      await fetch(`/admin/button-groups/${g.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, credentials:'same-origin', body: JSON.stringify({ title: nt }) });
      await refreshGroupsList(); await preloadGroups(); fillGroupSelect();
      showToast?.({ title:'Сохранено' });
    };
    const del = makeIconBtn({ variant:'danger', title:'Удалить группу', icon:ICONS.trash });
    del.onclick = async ()=>{
      if (!confirm('Удалить группу? Кнопки останутся без группы.')) return;
      await fetch(`/admin/button-groups/${g.id}`, { method:'DELETE', credentials:'same-origin' });
      await refreshGroupsList(); await preloadGroups(); fillGroupSelect();
      showToast?.({ title:'Удалено' });
    };
    right.appendChild(edit); right.appendChild(del);
    top.appendChild(left); top.appendChild(right);
    el.appendChild(top);

    // Состав группы + снятие из группы
    const items = itemsByGroup[g.id] || [];
    const ul = document.createElement('div');
    ul.className = 'sub-list';
    if (items.length === 0){
      const empty = document.createElement('div'); empty.className = 'muted small'; empty.textContent = 'Кнопок в группе нет'; ul.appendChild(empty);
    } else {
      items.forEach(b => {
        const row = document.createElement('div'); row.className = 'row'; row.style.justifyContent='space-between';
        const left = document.createElement('div'); left.textContent = b.title;
        const right = document.createElement('div');
        const remove = makeIconBtn({ variant:'danger', title:'Убрать из группы', icon:ICONS.trash });
        remove.onclick = async ()=>{
          try{
            const res = await fetch(`/admin/buttons/${b.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, credentials:'same-origin', body: JSON.stringify({ group_id: null }) });
            if(!res.ok){ const t = await res.text(); throw new Error(t||'Не удалось обновить кнопку'); }
            await refreshGroupsList();
            await fetchButtons();
            showToast?.({ title:'Удалено из группы', type:'success' });
          }catch(err){ console.error(err); showToast?.({ title:'Ошибка', message: err.message||'', type:'error' }); }
        };
        right.appendChild(remove);
        row.appendChild(left); row.appendChild(right);
        ul.appendChild(row);
      });
    }
    el.appendChild(ul);

    list.appendChild(el);
  });
}

function openBtnForm(existing){
  btnEditingId = existing?.id ?? null;

  btnTitle.value    = existing?.title || '';
  btnBg.value       = existing?.bg_color || '#2563eb';
  btnFg.value       = existing?.text_color || '#ffffff';
  if (btnIconPath) btnIconPath.textContent = existing?.icon_path || '';
  fillTargetSelect(existing?.target_slug);
  fillGroupSelect(existing?.group_id || '');

  if (btnPalette){
    let matched = false;
    btnPalette.querySelectorAll('.swatch').forEach(s =>{
      if (s.title.toLowerCase() === (btnBg.value || '').toLowerCase()){ s.classList.add('selected'); matched = true; }
      else s.classList.remove('selected');
    });
    if (!matched) btnPalette.querySelectorAll('.swatch').forEach(s => s.classList.remove('selected'));
  }

  document.getElementById('btnModalTitle').textContent = btnEditingId ? 'Редактировать кнопку' : 'Новая кнопка';
  btnModal.classList.add('open');
  btnModal.setAttribute('aria-hidden', 'false');
}

function closeBtnForm(){
  btnModal.classList.remove('open');
  btnModal.setAttribute('aria-hidden', 'true');
  btnEditingId = null;
}

async function saveBtnForm(){
  const title = (btnTitle?.value || '').trim();
  const target_slug = btnTarget?.value || '';
  const bg_color = btnBg?.value || '#2563eb';
  const text_color = btnFg?.value || '#ffffff';
  const icon_path = (btnIconPath?.textContent || '').trim() || null;

  if (!title) return alert('Введите название');
  if (!target_slug) return alert('Выберите страницу');

  const group_id_raw = (document.getElementById('btnGroup')?.value || '').trim();
  const payload = { title, target_slug, bg_color, text_color, icon_path, group_id: group_id_raw ? Number(group_id_raw) : null };

  try{
    let res;
    if (btnEditingId){
      res = await fetch(`/admin/buttons/${btnEditingId}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/admin/buttons', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
    }

    if (!res.ok){
      const txt = await res.text();
      throw new Error(txt || 'Не удалось сохранить кнопку');
    }

    closeBtnForm();
    showToast?.({ title: 'Сохранено', type: 'success' });
    await fetchButtons();
  }catch(err){
    console.error(err);
    showToast?.({ title: 'Ошибка', message: err.message || 'Не удалось сохранить', type: 'error' });
  }
}

// Встроим «Изменить» в список + уберём DnD (не нужен)

// ========================= Pages (list + modal) =========================
let pageModal, pageTitle, pageIsHome, pageSave, pageCancel, pageClose;
let pageEditingSlug = null;

function initPagesUI(){
  if (pageModal) return; // 1 раз
  pageModal   = document.getElementById('pageModal');
  pageTitle   = document.getElementById('pageTitle');
  pageIsHome  = document.getElementById('pageIsHome');
  pageSave    = document.getElementById('pageSave');
  pageCancel  = document.getElementById('pageCancel');
  pageClose   = document.getElementById('pageClose');

  const openPageBtn = document.getElementById('openPageModal');
  if (openPageBtn) openPageBtn.onclick = () => openPageForm();

  if (pageCancel) pageCancel.onclick = closePageForm;
  if (pageClose)  pageClose.onclick  = closePageForm;
  if (pageSave)   pageSave.onclick   = savePageForm;

  refreshPagesList();
}

function openPageForm(existing){
  pageEditingSlug = existing?.slug ?? null;
  // slug скрыт и недоступен для редактирования — генерируется автоматически
  pageTitle.value   = existing?.title || '';
  pageIsHome.checked = !!existing?.is_home;

  document.getElementById('pageModalTitle').textContent = pageEditingSlug ? 'Редактировать страницу' : 'Новая страница';
  pageModal.classList.add('open');
  pageModal.setAttribute('aria-hidden', 'false');
}
function closePageForm(){
  pageModal.classList.remove('open');
  pageModal.setAttribute('aria-hidden', 'true');
  pageEditingSlug = null;
}

async function savePageForm(){
  const title = (pageTitle?.value || "").trim();
  const is_home = !!pageIsHome?.checked;
  if (!title) return alert("Введите заголовок страницы");
  try {
    let res;
    if (pageEditingSlug) {
      res = await fetch(`/admin/pages/${pageEditingSlug}`, {
        method: "PUT", headers: {"Content-Type":"application/json"}, credentials: "same-origin",
        body: JSON.stringify({ title, is_home })
      });
    } else {
      let slug = ("p-" + Date.now().toString(36)).slice(0,80);


      res = await fetch("/admin/pages", {
        method: "POST", headers: {"Content-Type":"application/json"}, credentials: "same-origin",
        body: JSON.stringify({ slug, title, is_home })
      });
    }
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(txt || "Не удалось сохранить страницу");
    }
    showToast?.({ title:"Сохранено", type:"success" });
    closePageForm();
    await refreshPagesList();
  } catch (err) {
    console.error(err);
    showToast?.({ title:"Ошибка", message: err.message || "Не удалось сохранить", type:"error" });
  }
}
async function refreshPagesList(){
  const list = document.getElementById('pagesList');
  if(!list) return;
  const res = await fetch('/admin/pages', { credentials:'same-origin' });
  const pages = await res.json();

  list.innerHTML = '';
  pages.forEach(p => {
    const el = document.createElement('div');
    el.className = 'item';

    const top = document.createElement('div');
    top.className = 'top';

    const left = document.createElement('div');
    const t = document.createElement('div');
    t.className = 'title';
    t.textContent = p.title;
    left.appendChild(t);

    const right = document.createElement('div');
    right.className = 'actions';

    const pick = makeIconBtn({ variant:'secondary', title:'Выбрать', icon:ICONS.pick });
pick.onclick = async ()=>{
  await loadPageBySlug(p.slug);
  document.getElementById('currentPageTitle').textContent = `Содержимое — ${p.title}`;
  showToast?.({ title:'Загружено', message:`Страница «${p.title}»`, type:'success' });
};

const edit = makeIconBtn({ variant:'ghost', title:'Изменить', icon:ICONS.edit });
edit.onclick = ()=> openPageForm(p);

const setHome = makeIconBtn({ variant: p.is_home ? 'success' : 'secondary', title: p.is_home ? 'Главная' : 'Сделать главной', icon:ICONS.home });
setHome.disabled = !!p.is_home;
setHome.onclick = async ()=>{
  await fetch(`/admin/pages/${p.slug}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    credentials:'same-origin',
    body: JSON.stringify({ is_home: true })
  });
  await refreshPagesList();
  showToast?.({ title:'Обновлено', message:'Главная страница изменена', type:'success' });
};

const del = makeIconBtn({ variant:'danger', title:'Удалить', icon:ICONS.trash });
del.onclick = async ()=>{
  if(!confirm('Удалить страницу?')) return;
  await fetch(`/admin/pages/${p.slug}`, { method:'DELETE', credentials:'same-origin' });
  await refreshPagesList();
  showToast?.({ title:'Удалено' });
};

right.appendChild(pick);
right.appendChild(edit);
right.appendChild(setHome);
right.appendChild(del);

    top.appendChild(left);
    top.appendChild(right);
    el.appendChild(top);

    if (p.is_home){
      const badge = document.createElement('div');
      badge.className = 'badge';
      badge.textContent = 'Главная';
      el.appendChild(badge);
    }

    list.appendChild(el);
  });
}


// ========================= Block Modal (Create/Edit) =========================
let blockModal, blockModalTitle, blockClose, blockCancel, blockSave;
let blockKindRadios, blockTextWrap, blockMediaWrap, blockQuill;
let blockFile, blockPick, blockUpload, blockUploadedPath, blockUrl;
let blockEditing = { mode:'create', id:null, kind:'text' };

function initBlocksUI(){
  if (blockModal) return; // один раз
  blockModal      = document.getElementById('blockModal');
  blockModalTitle = document.getElementById('blockModalTitle');
  blockClose      = document.getElementById('blockClose');
  blockCancel     = document.getElementById('blockCancel');
  blockSave       = document.getElementById('blockSave');

  blockTextWrap   = document.getElementById('blockTextWrap');
  blockMediaWrap  = document.getElementById('blockMediaWrap');
  blockKindRadios = document.querySelectorAll('input[name="blockKind"]');

  blockFile        = document.getElementById('blockFile');
  blockPick        = document.getElementById('blockPick');
  blockUpload      = document.getElementById('blockUpload');
  blockUploadedPath= document.getElementById('blockUploadedPath');
  blockUrl         = document.getElementById('blockUrl');

  if (typeof Quill !== "undefined") {
    blockQuill = new Quill('#blockQuill', {
      theme: 'snow',
      modules: { toolbar: [
        [{'header':[1,2,3,false]}],
        ['bold','italic','underline','strike'],
        [{'list':'ordered'},{'list':'bullet'}],
        ['link','blockquote','code-block'],
        [{'align':[]}],
        ['clean']
      ]}
    });
  } else {
    blockQuill = null;
  }

  const openBtn = document.getElementById('openBlockModal');
  if(openBtn) openBtn.onclick = ()=> openBlockModal({ mode:'create' });

  if(blockClose)  blockClose.onclick  = closeBlockModal;
  if(blockCancel) blockCancel.onclick = closeBlockModal;
  if(blockSave)   blockSave.onclick   = saveBlockModal;

  blockKindRadios.forEach(r => r.addEventListener('change', updateBlockKindView));

  if(blockPick)   blockPick.onclick = ()=> blockFile && blockFile.click();
  if(blockUpload) blockUpload.onclick = async ()=>{
    if(!blockFile || !blockFile.files || !blockFile.files[0]){
      showToast?.({ title:'Файл не выбран', type: 'error' });
      return;
    }
    const p = await uploadFile(blockFile.files[0]);
    blockUploadedPath.textContent = p;
    showToast?.({ title:'Файл загружен', message:p });
  };

  updateBlockKindView();
}

function updateBlockKindView(){
  const kind = getSelectedBlockKind();
  const textMode  = (kind === 'text');
  blockTextWrap.style.display  = textMode ? '' : 'none';
  blockMediaWrap.style.display = textMode ? 'none' : '';
}

function getSelectedBlockKind(){
  const r = Array.from(blockKindRadios).find(x => x.checked);
  return r ? r.value : 'text';
}

function openBlockModal({ mode='create', block=null }={}){
  blockEditing.mode = mode;
  blockEditing.id   = block?.id || null;

  const kind = block?.kind || 'text';
  blockKindRadios.forEach(r => r.checked = (r.value === kind));
  updateBlockKindView();

  blockUploadedPath.textContent = '';
  blockUrl.value = '';
  blockFile.value = '';

  if(kind === 'text'){
    blockQuill.setContents([]);
    if (block?.content?.html) blockQuill.clipboard.dangerouslyPasteHTML(block.content.html);
  } else {
    const path = block?.content?.path || '';
    blockUploadedPath.textContent = path;
    blockUrl.value = path.startsWith('http') ? path : '';
  }

  blockModalTitle.textContent = (mode === 'edit') ? 'Изменить блок' : 'Новый блок';
  blockModal.classList.add('open');
  blockModal.setAttribute('aria-hidden','false');
}

function closeBlockModal(){
  blockModal.classList.remove('open');
  blockModal.setAttribute('aria-hidden','true');
  blockEditing = { mode:'create', id:null, kind:'text' };
}

async function saveBlockModal(){
  if(!currentPage){ alert('Сначала выберите/загрузите страницу'); return; }

  const kind = getSelectedBlockKind();
  let content = {};

  if(kind === 'text'){
    const raw = blockQuill.root.innerHTML.trim();
    const html = normalizeQuillHtml(raw);
    content = { html };
  } else {
    const uploaded = (blockUploadedPath.textContent || '').trim();
    const url = (blockUrl.value || '').trim();
    const path = uploaded || url;
    if(!path) return alert('Укажите файл или URL');
    content = { path };
  }

  try{
    let res;
    if(blockEditing.mode === 'edit' && blockEditing.id){
      res = await fetch(`/admin/blocks/${blockEditing.id}`, {
        method:'PUT',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ kind, content })
      });
    }else{
      res = await fetch('/admin/blocks', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({ page_id: currentPage.id, kind, content })
      });
    }
    if(!res.ok){
      const txt = await res.text();
      throw new Error(txt || 'Не удалось сохранить блок');
    }
    closeBlockModal();
    await loadPage();
    showToast?.({ title:'Сохранено', type:'success' });
  }catch(err){
    console.error(err);
    showToast?.({ title:'Ошибка', message: err.message || 'Не удалось сохранить', type:'error' });
  }
}







