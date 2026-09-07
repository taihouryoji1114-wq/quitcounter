"""Visual-only theme support for Future Financials."""

from __future__ import annotations


DEFAULT_THEME = "normal"
THEMES = frozenset({"normal", "godot"})
STORAGE_KEY = "mirai-kessan-ui-theme"


def normalize_theme(value):
    """Normalize a theme code and safely fall back to NORMAL."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in THEMES else DEFAULT_THEME


def theme_head_html():
    """Load the saved visual preference before the page is painted."""
    return f"""
    <link rel="stylesheet" href="/static/mirai_kessan_themes.css">
    <script>
      (() => {{
        const key = {STORAGE_KEY!r};
        const allowed = new Set(['normal', 'godot']);
        let selected = 'normal';
        try {{
          const saved = String(localStorage.getItem(key) || '').trim().toLowerCase();
          selected = allowed.has(saved) ? saved : 'normal';
          if (!allowed.has(saved) && saved) localStorage.setItem(key, 'normal');
        }} catch (_) {{ selected = 'normal'; }}
        document.documentElement.dataset.miraiTheme = selected;
        window.miraiTheme = {{
          current: () => document.documentElement.dataset.miraiTheme || 'normal',
          set: code => {{
            const next = String(code || '').trim().toLowerCase();
            if (!allowed.has(next)) return false;
            document.documentElement.dataset.miraiTheme = next;
            try {{ localStorage.setItem(key, next); }} catch (_) {{}}
            return true;
          }},
        }};
      }})();
    </script>
    """


def theme_controls_html():
    """Hidden, non-security theme-code console shared by all Mirai pages."""
    return """
    <div id="mirai-theme-console" class="mirai-theme-console" aria-hidden="true">
      <button type="button" class="mirai-theme-backdrop" data-theme-close aria-label="閉じる"></button>
      <section class="mirai-theme-console-card" role="dialog" aria-modal="true" aria-labelledby="mirai-theme-console-title">
        <div class="mirai-theme-console-kicker">DEVELOPER / THEME CODE</div>
        <h2 id="mirai-theme-console-title">THEME CODE</h2>
        <p>外観だけを切り替えます。経営データや計算結果は変わりません。</p>
        <input id="mirai-theme-code" type="text" inputmode="text" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="ENTER ACCESS CODE" aria-label="テーマコード">
        <div id="mirai-theme-code-error" class="mirai-theme-code-error" aria-live="polite"></div>
        <div class="mirai-theme-console-actions">
          <button type="button" data-theme-close>キャンセル</button>
          <button type="button" id="mirai-theme-apply">適用</button>
        </div>
      </section>
    </div>
    <div id="mirai-theme-toast" class="mirai-theme-toast" role="status" aria-live="polite"></div>
    <script>
      (() => {
        if (window.__miraiThemeConsoleReady) return;
        window.__miraiThemeConsoleReady = true;
        const consoleEl = document.getElementById('mirai-theme-console');
        const input = document.getElementById('mirai-theme-code');
        const error = document.getElementById('mirai-theme-code-error');
        const toast = document.getElementById('mirai-theme-toast');
        let taps = 0;
        let tapTimer = 0;
        const close = () => {
          consoleEl.classList.remove('open');
          consoleEl.setAttribute('aria-hidden', 'true');
          input.value = '';
          error.textContent = '';
        };
        const open = () => {
          consoleEl.classList.add('open');
          consoleEl.setAttribute('aria-hidden', 'false');
          setTimeout(() => input.focus(), 80);
        };
        const showToast = message => {
          toast.textContent = message;
          toast.classList.add('show');
          setTimeout(() => toast.classList.remove('show'), 1800);
        };
        document.addEventListener('click', event => {
          const target = event.target.closest('button,[role="button"],div,span');
          if (!target || target.textContent.trim() !== '未来決算') return;
          clearTimeout(tapTimer);
          taps += 1;
          if (taps >= 5) { taps = 0; open(); return; }
          tapTimer = setTimeout(() => { taps = 0; }, 2400);
        });
        document.querySelectorAll('[data-theme-close]').forEach(button => button.addEventListener('click', close));
        const apply = () => {
          const code = input.value.trim().toLowerCase();
          if (!window.miraiTheme || !window.miraiTheme.set(code)) {
            error.textContent = '使用できないテーマコードです';
            return;
          }
          close();
          showToast('テーマを変更しました');
        };
        document.getElementById('mirai-theme-apply').addEventListener('click', apply);
        input.addEventListener('keydown', event => {
          if (event.key === 'Enter') apply();
          if (event.key === 'Escape') close();
        });
      })();
    </script>
    """
