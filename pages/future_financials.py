from datetime import date

from nicegui import ui

from core.auth import require_login
from core.purchases import purchases
from core.theme import Theme


@ui.page("/mirai-kessan")
def future_financials():
    if not require_login():
        return
    Theme.page("未来決算")
    content = Theme.shell(
        "未来決算",
        "会社のお金を、利益と資金繰りに分けて見える化",
        back_to="/",
    )
    current_month = date.today().strftime("%Y-%m")
    purchase_total = purchases.monthly_total(current_month, kind="cost")
    other_expense_total = purchases.monthly_total(current_month, kind="expense")
    with content:
        with ui.card().classes("surface-card w-full q-pa-md q-mb-md"):
            ui.label("仕入れノート連携").classes("section-kicker")
            ui.label(
                f"{current_month.replace('-', '年')}月の仕入れ実績　¥{purchase_total:,}"
            ).classes("text-xl font-bold q-mt-xs")
            ui.label(
                f"その他経費　¥{other_expense_total:,}"
            ).classes("text-sm font-bold q-mt-xs")
            ui.label(
                "今月の仕入れ合計を、下の売上原価へ自動反映しています"
                if purchase_total else
                "今月の仕入れを入力すると、売上原価へ自動反映されます"
            ).classes("text-xs text-grey-7 q-mt-xs")
        ui.html(
            r'''
<div id="mirai-app">
  <section class="mk-card input-card">
    <div class="mk-head"><div><small>PLAN</small><h2>月間計画を入力</h2></div><button id="save-plan">保存</button></div>
    <div class="input-grid">
      <label>売上高<input id="sales" inputmode="numeric" value="3000000"></label>
      <label>売上原価<input id="cogs" inputmode="numeric" value="1200000"></label>
      <label>人件費<input id="personnel" inputmode="numeric" value="700000"></label>
      <label>その他一般管理費<input id="other-sga" inputmode="numeric" value="400000"></label>
      <label>営業外収益<input id="non-op-income" inputmode="numeric" value="0"></label>
      <label>営業外費用・支払利息<input id="non-op-expense" inputmode="numeric" value="50000"></label>
      <label>目標経常利益<input id="target-profit" inputmode="numeric" value="700000"></label>
    </div>
  </section>

  <section class="mk-card result-card">
    <div class="mk-head"><div><small>PROFIT</small><h2>R-BASE 利益ブロック図</h2></div><span>月間</span></div>
    <p class="block-guide">売上が、変動費・粗利・固定費・利益へどう分かれるかを面積で表示します。</p>
    <div id="profit-summary" class="summary-grid"></div>
    <div id="profit-map" class="box-map" aria-label="売上を変動費、粗利、人件費、その他固定費、利益に分解した図"></div>
    <div id="sales-answer" class="answer"></div>
  </section>

  <section class="mk-card cash-card">
    <div class="mk-head"><div><small>CASH</small><h2>資金繰り</h2></div><span>利益とは別に計算</span></div>
    <div class="input-grid compact">
      <label>消費税の支払<input id="consumption-tax" inputmode="numeric" value="120000"></label>
      <label>法人税等<input id="corporate-tax" inputmode="numeric" value="120000"></label>
      <label>借入金の元金返済<input id="loan-payment" inputmode="numeric" value="200000"></label>
      <label>設備投資・その他<input id="investment" inputmode="numeric" value="0"></label>
    </div>
    <div id="cash-flow" class="cash-flow"></div>
  </section>
</div>
<style>
#mirai-app{width:100%;display:grid;gap:16px}.mk-card{background:#fff;border:1px solid #E5E9E6;border-radius:24px;padding:22px;box-shadow:0 8px 24px rgba(39,55,45,.055)}.mk-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.mk-head small{color:#4F7C68;font-weight:800;letter-spacing:.14em}.mk-head h2{font-size:19px;margin:3px 0 0}.mk-head span{color:#7A867F;font-size:11px}.mk-head button{border:0;border-radius:10px;background:#EDF5F0;color:#39745A;padding:9px 14px;font-weight:700}.block-guide{margin:-8px 0 14px;color:#748078;font-size:11px;line-height:1.6}.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.input-grid label{color:#68746D;font-size:10px;font-weight:700}.input-grid input{width:100%;box-sizing:border-box;margin-top:5px;border:1px solid #DDE3DF;border-radius:10px;padding:10px;font-size:14px;outline:none}.input-grid input:focus{border-color:#4F7C68;box-shadow:0 0 0 3px rgba(79,124,104,.1)}.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:18px}.summary{background:#F5F8F6;border-radius:12px;padding:12px}.summary small{display:block;color:#748078;font-size:9px}.summary b{display:block;margin-top:3px;font-size:15px}.summary.negative b{color:#C84B45}.profit-map{display:grid;gap:7px}.money-row{display:grid;grid-template-columns:84px 1fr 88px;gap:8px;align-items:center;font-size:11px}.money-track{height:30px;background:#F0F2F0;border-radius:7px;overflow:hidden}.money-bar{height:100%;min-width:2px;border-radius:7px;display:flex;align-items:center;padding:0 8px;box-sizing:border-box;color:#fff;font-size:9px;white-space:nowrap}.sales-bar{background:#355F4C}.cost-bar{background:#94A79D}.gross-bar{background:#4F8C70}.sga-bar{background:#C2A56E}.ordinary-bar{background:#4B77B7}.negative-bar{background:#C85C57}.money-value{text-align:right;font-weight:700}.answer{margin-top:18px;border-radius:15px;background:#EAF1FF;padding:16px;color:#244F89}.answer small{display:block;font-size:10px}.answer b{display:block;font-size:22px;margin-top:3px}.answer span{font-size:11px}.compact{margin-bottom:18px}.cash-flow{display:grid;gap:7px}.cash-line{display:grid;grid-template-columns:1fr auto;gap:10px;padding:10px 0;border-bottom:1px solid #EEF0EE;font-size:12px}.cash-line strong{font-size:14px}.cash-line.final{border:0;border-radius:12px;background:#F3F6F4;padding:14px}.cash-line.final strong.negative{color:#C84B45}@media(max-width:520px){.mk-card{padding:18px 15px}.input-grid{grid-template-columns:1fr}.summary-grid{grid-template-columns:1fr 1fr}.money-row{grid-template-columns:70px 1fr 78px}.money-track{height:27px}}
.box-map{height:360px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;background:#E8ECE9;padding:5px;border-radius:16px;overflow:hidden}.box-column{min-width:0;height:100%;display:flex;flex-direction:column;gap:5px}.box-spacer{min-height:0}.money-box{min-height:34px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;border-radius:11px;padding:7px;box-sizing:border-box;overflow:hidden;color:#fff}.money-box span{font-size:11px;font-weight:700}.money-box b{font-size:14px;margin-top:3px}.money-box em{font-size:9px;font-style:normal;margin-top:3px;opacity:.9}.box-sales{height:100%;background:#355F4C}.box-cost{background:#82988D}.box-gross{background:#4F8C70}.box-personnel{background:#B28C53}.box-other{background:#C3A976}.box-profit{background:#4B77B7}.box-loss{background:#C85C57}@media(max-width:520px){.box-map{height:300px;gap:3px;padding:3px}.box-column{gap:3px}.money-box{padding:4px}.money-box span{font-size:9px}.money-box b{font-size:11px}.money-box em{font-size:8px}}
</style>
            ''',
            sanitize=False,
        ).classes("w-full")
        ui.add_body_html(
            r'''
<script>
(() => {
  function init(){
    const root=document.getElementById('mirai-app');
    if(!root){setTimeout(init,100);return}
    const $=id=>document.getElementById(id), ids=['sales','cogs','personnel','other-sga','non-op-income','non-op-expense','target-profit','consumption-tax','corporate-tax','loan-payment','investment'];
    const num=id=>Math.max(0,Number(String($(id).value).replace(/,/g,''))||0), yen=n=>new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(n||0);
    function box(label,value,share,cls,note=''){return `<div class="money-box ${cls}" style="flex:${Math.max(share,.035)}"><span>${label}</span><b>${yen(value)}</b>${note?`<em>${note}</em>`:''}</div>`}
    function update(){
      const sales=num('sales'),cogs=num('cogs'),personnel=num('personnel'),otherSga=num('other-sga'),sga=personnel+otherSga,noi=num('non-op-income'),noe=num('non-op-expense'),target=num('target-profit');
      const gross=sales-cogs,operating=gross-sga,ordinary=operating+noi-noe,rate=sales?cogs/sales:0,required=(1-rate)>0?(sga+noe-noi+target)/(1-rate):0;
      $('profit-summary').innerHTML=[['粗利',gross],['営業利益',operating],['経常利益',ordinary]].map(x=>`<div class="summary ${x[1]<0?'negative':''}"><small>${x[0]}</small><b>${yen(x[1])}</b></div>`).join('');
      const base=Math.max(sales,1),costShare=Math.min(cogs/base,1),grossShare=Math.max(gross/base,0),personnelShare=personnel/base,otherShare=otherSga/base,profitShare=Math.max(operating/base,0);
      const pct=n=>`${(n*100).toFixed(1)}%`, laborShare=gross>0?personnel/gross:0;
      $('profit-map').innerHTML=`<div class="box-column">${box('売上',sales,1,'box-sales','100%')}</div><div class="box-column">${box('変動費（仕入・原価）',cogs,costShare,'box-cost',`原価率 ${pct(costShare)}`)}${box('粗利',gross,grossShare,gross<0?'box-loss':'box-gross',`粗利率 ${pct(grossShare)}`)}</div><div class="box-column"><div class="box-spacer" style="flex:${costShare}"></div>${box('人件費',personnel,personnelShare,'box-personnel',`労働分配率 ${pct(laborShare)}`)}${box('その他固定費',otherSga,otherShare,'box-other')}${box(operating<0?'営業損失':'営業利益',Math.abs(operating),Math.max(profitShare,Math.abs(operating)/base),operating<0?'box-loss':'box-profit',`営業利益率 ${pct(operating/base)}`)}</div>`;
      const gap=Math.max(0,required-sales);$('sales-answer').innerHTML=`<small>目標経常利益 ${yen(target)} に必要な売上</small><b>${yen(required)}</b><span>${gap>0?`現在の計画より ${yen(gap)} 増やす必要があります`:'現在の売上計画で達成圏内です'}</span>`;
      const ct=num('consumption-tax'),corp=num('corporate-tax'),loan=num('loan-payment'),inv=num('investment'),cash=ordinary-corp-ct-loan-inv;
      $('cash-flow').innerHTML=`<div class="cash-line"><span>経常利益からスタート</span><strong>${yen(ordinary)}</strong></div><div class="cash-line"><span>税金の支払</span><strong>− ${yen(ct+corp)}</strong></div><div class="cash-line"><span>借入元金・設備投資</span><strong>− ${yen(loan+inv)}</strong></div><div class="cash-line final"><span>手元資金の増減目安</span><strong class="${cash<0?'negative':''}">${yen(cash)}</strong></div>`;
    }
    ids.forEach(id=>$(id).addEventListener('input',update));
    try{const saved=JSON.parse(localStorage.getItem('habitory-future-plan')||'null');if(saved){ids.forEach(id=>{if(saved[id]!==undefined)$(id).value=saved[id]});if(saved.sga!==undefined&&saved.personnel===undefined){$('personnel').value=Math.round(saved.sga*.65);$('other-sga').value=Math.round(saved.sga*.35)}}}catch(e){}
    $('save-plan').onclick=()=>{const data={};ids.forEach(id=>data[id]=$(id).value);localStorage.setItem('habitory-future-plan',JSON.stringify(data));$('save-plan').textContent='保存しました';setTimeout(()=>$('save-plan').textContent='保存',1400)};
    update();
  }
  init();
})();
</script>
            '''
        )
        if purchase_total:
            ui.add_body_html(
                f'''<script>
function applyPurchaseTotal(attempt = 0) {{
  const cogs = document.getElementById('cogs');
  if (cogs) {{
    cogs.value = {purchase_total};
    cogs.dispatchEvent(new Event('input', {{bubbles:true}}));
  }} else if (attempt < 20) {{
    setTimeout(() => applyPurchaseTotal(attempt + 1), 100);
  }}
}}
applyPurchaseTotal();
</script>'''
            )
        if other_expense_total:
            ui.add_body_html(
                f'''<script>
function applyOtherExpense(attempt = 0) {{
  const other = document.getElementById('other-sga');
  if (other) {{
    other.value = {other_expense_total};
    other.dispatchEvent(new Event('input', {{bubbles:true}}));
  }} else if (attempt < 20) {{
    setTimeout(() => applyOtherExpense(attempt + 1), 100);
  }}
}}
applyOtherExpense();
</script>'''
            )
