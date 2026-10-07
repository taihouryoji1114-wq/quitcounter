window.coupleHold = (e, emit) => {
  const root = e.currentTarget;
  const heart = e.target.closest('[data-heart]');
  if (!heart || root.dataset.done === 'true' || (e.pointerType === 'mouse' && e.button !== 0)) return;
  e.preventDefault();
  if (!root.hold) {
    const status = root.querySelector('[data-status]');
    const state = root.hold = { pointers: new Map(), timer: null, start: 0 };
    const reset = () => {
      clearInterval(state.timer); state.timer = null; state.pointers.clear();
      root.querySelectorAll('[data-heart]').forEach(h => h.classList.remove('holding'));
      if (root.dataset.done !== 'true') status.textContent = '左右のハートを、ふたりで3秒長押し';
      window.removeEventListener('blur', reset);
      document.removeEventListener('visibilitychange', reset);
    };
    state.reset = reset;
    ['pointerup','pointercancel','lostpointercapture'].forEach(type => root.addEventListener(type, reset));
    root.addEventListener('pointermove', ev => {
      const held = state.pointers.get(ev.pointerId);
      if (!held) return;
      const r = held.getBoundingClientRect();
      if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) reset();
    });
  }
  const s = root.hold;
  if ([...s.pointers.values()].includes(heart)) return;
  s.pointers.set(e.pointerId, heart); heart.classList.add('holding');
  root.setPointerCapture(e.pointerId);
  window.addEventListener('blur', s.reset);
  document.addEventListener('visibilitychange', s.reset);
  const status = root.querySelector('[data-status]');
  status.textContent = 'もうひとつのハートにも指を置いてね';
  if (s.pointers.size !== 2 || s.timer) return;
  s.start = performance.now();
  status.textContent = 'そのまま… 3';
  s.timer = setInterval(() => {
    if (!root.isConnected || document.hidden) { s.reset(); return; }
    const left = 3000 - (performance.now() - s.start);
    status.textContent = `そのまま… ${Math.max(1, Math.ceil(left / 1000))}`;
    if (left <= 0) {
      root.dataset.done = 'true'; s.reset();
      status.textContent = 'ありがとうが重なりました 🌸';
      emit();
    }
  }, 50);
};
