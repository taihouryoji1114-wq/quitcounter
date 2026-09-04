// Runs only on the open page. No background/lock-screen alarm is promised.
(() => {
  if (window.chankoAnnouncements) return;
  let active = false, context = null, lastTest = 0, startButton = null;
  let wakeLock = null, rowsCache = [], syncTime = 0, serverTime = 0, lastPlayed = '', error = '';
  const inFlight = new Set(), played = new Map();
  let speechReady = false;
  const api = window.chankoAnnouncements = {};
  const showStatus = () => {
    let text = !active ? '停止中：このiPadで「店内スピーカーを開始」を押してください' :
      error || (!speechReady ? '開始音声を確認中…' : context?.state !== 'running' ? '音声が中断されています。開始ボタンを押し直してください' :
        '待機中：この画面を開いたままにしてください');
    if (active && syncTime && Date.now() - syncTime > 60000) text += '（通信が途切れています。保存済みの時刻で動作中）';
    document.querySelectorAll('[data-announcement-status]').forEach(el => { el.textContent = text; });
    document.querySelectorAll('[data-announcement-lock]').forEach(el => {
      el.textContent = wakeLock && !wakeLock.released ? '画面の自動ロックを防止中' : '自動ロック防止は未有効。iPadの自動ロック設定も確認してください';
    });
    document.querySelectorAll('[data-announcement-last]').forEach(el => { el.textContent = lastPlayed || 'まだ再生していません'; });
  };
  const keepAwake = async () => {
    if (!active || !navigator.wakeLock || document.visibilityState !== 'visible') return;
    try { wakeLock = await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release', showStatus); } catch (_) {}
    showStatus();
  };
  api.enable = async button => {
    try {
      context = context || new (window.AudioContext || window.webkitAudioContext)();
      // Unlock speech synchronously inside the iPad tap, not after a timer/await.
      active = true; error = ''; speechReady = false;
      const resumed = context.resume();
      if (!window.speechSynthesis) throw new Error('speech unavailable');
      speechSynthesis.cancel();
      const welcome = new SpeechSynthesisUtterance('店内スピーカーを開始します。');
      welcome.lang = 'ja-JP';
      welcome.onstart = () => { speechReady = true; lastPlayed = '開始音声を再生しました'; showStatus(); };
      welcome.onerror = () => { error = '音声を再生できません。開始ボタンを押し直してください'; showStatus(); };
      speechSynthesis.speak(welcome);
      setTimeout(() => { if (active && !speechReady) { error = '開始音声を確認できません。開始ボタンを押し直してください'; showStatus(); } }, 10000);
      await resumed;
      await keepAwake();
      startButton = button || startButton;
      if (startButton) startButton.querySelector('.q-btn__content').textContent = '音声ON';
      showStatus();
    } catch (_) { active = false; error = '音声を開始できませんでした'; showStatus(); alert('音声を開始できませんでした。端末の音量・ブラウザ設定を確認してください。'); }
  };
  api.stop = () => {
    active = false; window.speechSynthesis?.cancel();
    wakeLock?.release(); wakeLock = null; showStatus();
    if (startButton) startButton.querySelector('.q-btn__content').textContent = '音声開始';
  };
  api.play = (text, onStarted = () => {}, onFailed = () => {}) => {
    if (!active || !context || context.state !== 'running') { showStatus(); return false; }
    const start = context.currentTime;
    [880, 660].forEach((hz, i) => {
      const oscillator = context.createOscillator(), gain = context.createGain();
      oscillator.frequency.value = hz;
      gain.gain.setValueAtTime(0, start + i * .35);
      gain.gain.linearRampToValueAtTime(.12, start + i * .35 + .015);
      gain.gain.exponentialRampToValueAtTime(.001, start + i * .35 + .32);
      oscillator.connect(gain); gain.connect(context.destination);
      oscillator.start(start + i * .35); oscillator.stop(start + i * .35 + .34);
    });
    setTimeout(() => {
      if (!active || !window.speechSynthesis) { onFailed(); return; }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ja-JP'; utterance.rate = .95;
      let started = false;
      utterance.onstart = () => { started = true; error = ''; lastPlayed = text; onStarted(); showStatus(); };
      utterance.onerror = () => { error = '読み上げに失敗しました。開始ボタンを押し直してください'; onFailed(); showStatus(); };
      setTimeout(() => { if (!started) { error = '音声の開始を確認できません。開始ボタンを押し直してください'; onFailed(); showStatus(); } }, 15000);
      speechSynthesis.speak(utterance);
    }, 750);
    return true;
  };
  api.test = async text => {
    if (Date.now() - lastTest < 10000) return;
    lastTest = Date.now();
    if (!active) {
      await api.enable();
    }
    api.play(text);
  };
  api.tick = (rows, minute) => {
    rowsCache = rows;
    serverTime = Date.parse(minute.replace(' ', 'T') + ':00+09:00');
    syncTime = Date.now();
    scan(rows, minute);
  };
  api.sync = (rows, timestamp) => {
    rowsCache = rows; serverTime = Date.parse(timestamp); syncTime = Date.now();
    showStatus();
    return {active, ready: active && speechReady && !error && context?.state === 'running' && document.visibilityState === 'visible', lastPlayed};
  };
  const scan = (rows, minute) => {
    if (!active || document.visibilityState !== 'visible') return;
    for (const row of rows) {
      if (!row.enabled || row.time !== minute.slice(11, 16)) continue;
      // Shared across tabs: one announcement per device/day, never catch up old alarms.
      const key = 'chanko-announcement:' + row.id;
      const stamp = minute.slice(0, 10);
      if (inFlight.has(key) || played.get(key) === stamp) continue;
      let previous;
      try { previous = localStorage.getItem(key); } catch (_) {}
      if (previous === stamp) continue;
      inFlight.add(key);
      const failed = () => { setTimeout(() => inFlight.delete(key), 20000); };
      if (!api.play(row.message, () => {
        played.set(key, stamp); inFlight.delete(key);
        try { localStorage.setItem(key, stamp); } catch (_) {}
      }, failed)) inFlight.delete(key);
    }
  };
  setInterval(() => {
    if (syncTime) {
      const japan = new Date(serverTime + Date.now() - syncTime + 9 * 60 * 60 * 1000);
      scan(rowsCache, japan.toISOString().slice(0, 16).replace('T', ' '));
    }
    showStatus();
  }, 1000);
  document.addEventListener('visibilitychange', () => { if (active) keepAwake(); showStatus(); });
})();
