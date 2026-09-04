// Runs only on the open page. No background/lock-screen alarm is promised.
(() => {
  if (window.chankoAnnouncements) return;
  let active = false, context = null, lastTest = 0, startButton = null;
  const api = window.chankoAnnouncements = {};
  api.enable = async button => {
    try {
      context = context || new (window.AudioContext || window.webkitAudioContext)();
      await context.resume();
      active = true;
      startButton = button || startButton;
      if (startButton) startButton.querySelector('.q-btn__content').textContent = '音声ON';
      api.play('アナウンスを開始します。');
    } catch (_) { alert('音声を開始できませんでした。端末の音量・ブラウザ設定を確認してください。'); }
  };
  api.stop = () => {
    active = false; window.speechSynthesis?.cancel();
    if (startButton) startButton.querySelector('.q-btn__content').textContent = '音声開始';
  };
  api.play = text => {
    if (!context || context.state !== 'running') return false;
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
      if (!active || !window.speechSynthesis) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ja-JP'; utterance.rate = .95;
      speechSynthesis.speak(utterance);
    }, 750);
    return true;
  };
  api.test = async text => {
    if (Date.now() - lastTest < 10000) return;
    lastTest = Date.now();
    if (!active) {
      context = context || new (window.AudioContext || window.webkitAudioContext)();
      await context.resume(); active = true;
    }
    api.play(text);
  };
  api.tick = (rows, minute) => {
    if (!active || document.visibilityState !== 'visible') return;
    for (const row of rows) {
      if (!row.enabled || row.time !== minute.slice(11, 16)) continue;
      // Shared across tabs: one announcement per device/day, never catch up old alarms.
      const key = 'chanko-announcement:' + row.id;
      try {
        if (localStorage.getItem(key) === minute.slice(0, 10)) continue;
        if (api.play(row.message)) localStorage.setItem(key, minute.slice(0, 10));
      } catch (_) { /* Storage-disabled browsers do not repeat alarms. */ }
    }
  };
})();
