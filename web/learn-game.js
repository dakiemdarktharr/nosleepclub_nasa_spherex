// The ship owns its rendering lifecycle; the host owns navigation and the journal.
export function mountLearnGame(root) {
  const get = id => document.getElementById(id);
  const stage = get('learn-game-stage');
  const loading = get('learn-game-loading');
  const library = get('learn-library');
  const qr = get('learn-qr-dialog');
  const t = key => window.SpherexSite.text(key);
  let frame = null, active = false, ready = false, deadline, libraryLoad;

  function send(extra = {}) {
    frame?.contentWindow?.postMessage({
      type: 'spherex:game-state', active: active && library.hidden && !qr?.open && !document.hidden,
      language: window.SpherexSite.language(), theme: document.documentElement.dataset.theme,
      ...extra,
    }, location.origin);
  }
  function resize() {
    const height = document.querySelector('.public-header').getBoundingClientRect().height;
    root.style.setProperty('--learn-header-height', `${height}px`);
  }
  new ResizeObserver(resize).observe(document.querySelector('.public-header'));
  function translate() {
    if (frame) frame.title = t('learnGameFrame');
    send();
  }
  function loadLibrary() {
    if (libraryLoad) return libraryLoad;
    get('learn-load-status').hidden = false;
    get('learn-load-status').dataset.copy = 'learnLoading';
    get('learn-load-status').textContent = t('learnLoading');
    get('learn-load-retry').hidden = true;
    libraryLoad = import('./learn.js?v=2').then(({mountLearn}) => {
      mountLearn(root, window.SpherexSite.language);
      get('learn-load-status').hidden = true;
    }).catch(() => {
      libraryLoad = null;
      get('learn-load-status').dataset.copy = 'learnError';
      get('learn-load-status').textContent = t('learnError');
      get('learn-load-retry').hidden = false;
    });
    return libraryLoad;
  }
  function openLibrary() {
    if (!active) return;
    library.hidden = false;
    if (frame) frame.inert = true;
    send();
    get('learn-library-close').focus({preventScroll: true});
    loadLibrary();
  }
  function closeLibrary() {
    library.hidden = true;
    if (frame) frame.inert = false;
    send({focusBook: true});
  }
  function failed() {
    loading.hidden = false;
    get('learn-game-status').dataset.copy = 'learnGameError';
    get('learn-game-status').textContent = t('learnGameError');
    get('learn-game-retry').hidden = false;
  }
  function enter() {
    active = true;
    resize();
    if (frame) { send(); return; }
    ready = false;
    loading.hidden = false;
    get('learn-game-status').dataset.copy = 'learnGameLoading';
    get('learn-game-status').textContent = t('learnGameLoading');
    get('learn-game-retry').hidden = true;
    frame = document.createElement('iframe');
    frame.id = 'learn-game-frame';
    frame.title = t('learnGameFrame');
    frame.src = `control-room.html?embedded=1&lang=${window.SpherexSite.language()}`;
    frame.addEventListener('load', () => send());
    frame.addEventListener('error', failed);
    stage.prepend(frame);
    deadline = setTimeout(() => { if (!ready) failed(); }, 45000);
    if (new URL(location.href).searchParams.get('library') === '1') {
      const url = new URL(location.href);
      url.searchParams.delete('library');
      history.replaceState(history.state, '', url);
      openLibrary();
    }
  }
  function leave() {
    active = false;
    send();
    clearTimeout(deadline);
    frame?.remove();
    frame = null;
    ready = false;
    library.hidden = true;
  }
  window.addEventListener('message', event => {
    if (!frame || event.source !== frame.contentWindow || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type === 'spherex:game-ready') {
      ready = true;
      clearTimeout(deadline);
      loading.hidden = true;
      send();
    } else if (data.type === 'spherex:book-open') openLibrary();
    else if (data.type === 'spherex:language' && ['vi', 'en'].includes(data.language)) {
      window.SpherexSite.apply(data.language);
    }
  });
  get('learn-library-close').addEventListener('click', closeLibrary);
  get('learn-game-retry').addEventListener('click', () => { leave(); enter(); });
  document.addEventListener('keydown', event => {
    if (active && !library.hidden && !qr?.open && event.key === 'Escape') { event.preventDefault(); closeLibrary(); }
  });
  document.addEventListener('spherex:language', translate);
  document.addEventListener('visibilitychange', () => send());
  if (qr) new MutationObserver(() => send()).observe(qr, {attributes: true, attributeFilter: ['open']});
  new MutationObserver(() => send()).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
  return {enter, leave};
}
