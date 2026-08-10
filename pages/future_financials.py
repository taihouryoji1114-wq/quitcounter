from datetime import date
import json

from nicegui import ui

from core.auth import log_out, require_login
from core.financials import financials
from core.purchases import purchases
from core.theme import Theme


@ui.page("/mirai-kessan")
def future_financials_home():
    if not require_login():
        return
    Theme.page("未来決算")
    def exit_action():
        ui.button(icon="logout", on_click=log_out).props(
            "flat round aria-label='R-BASEへ戻る'"
        ).classes(
            "text-grey-8"
        ).tooltip("R-BASEへ戻る")

    content = Theme.shell(
        "経営ダッシュボード",
        "毎日の入力から、今月の経営状況を見える化",
        action=exit_action,
        brand="未来決算",
    )
    current_month = date.today().strftime("%Y-%m")
    purchase_total = purchases.monthly_total(current_month, kind="cost")
    other_expense_total = purchases.monthly_total(current_month, kind="expense")
    sales_total = financials.monthly_sales_total(current_month)
    with content:
        with ui.element("div").classes("grid grid-cols-2 gap-3 w-full q-mb-md"):
            with ui.card().classes("surface-card q-pa-md col-span-2"):
                ui.label("今月の売上実績").classes("text-xs text-grey-6")
                ui.label(f"¥{sales_total:,}").classes("text-3xl font-bold metric-value")
            with ui.card().classes("surface-card q-pa-md"):
                ui.label("今月の原価仕入れ").classes("text-xs text-grey-6")
                ui.label(f"¥{purchase_total:,}").classes("text-xl font-bold metric-value")
            with ui.card().classes("surface-card q-pa-md"):
                ui.label("今月のその他経費").classes("text-xs text-grey-6")
                ui.label(f"¥{other_expense_total:,}").classes("text-xl font-bold metric-value")

        def menu_card(title, description, icon, color, path):
            with ui.card().classes(
                "habit-card w-full q-pa-lg q-mb-md cursor-pointer"
            ).on("click", lambda _, target=path: ui.navigate.to(target)):
                with ui.row().classes("w-full items-center no-wrap"):
                    with ui.element("div").classes(
                        "w-14 h-14 rounded-xl q-mr-md flex items-center justify-center"
                    ).style(f"background:{color}18;color:{color}"):
                        ui.icon(icon).classes("text-3xl")
                    with ui.column().classes("gap-0"):
                        ui.label(title).classes("text-xl font-bold")
                        ui.label(description).classes("text-grey-7 q-mt-xs")
                    ui.space()
                    ui.icon("chevron_right").classes("text-2xl text-grey-7")

        menu_card("売上入力", "その日の売上を記録", "payments", "#B87835", "/mirai-kessan/sales")
        menu_card("仕入れノート", "原価・経費・消費税を記録", "receipt_long", "#246BFD", "/shiire")
        menu_card("利益シミュレーション", "計画と暫定実績を図で比較", "account_tree", "#39745A", "/mirai-kessan/block-map")


@ui.page("/mirai-kessan/block-map")
def future_financials():
    if not require_login():
        return
    Theme.page("未来決算")
    content = Theme.shell(
        "利益シミュレーション",
        "計画と暫定実績を切り替えて、お金の残り方を確認",
        back_to="/mirai-kessan",
    )
    current_month = date.today().strftime("%Y-%m")
    actuals = {
        "sales": financials.monthly_sales_total(current_month),
        "cogs": purchases.monthly_total(current_month, kind="cost"),
        "other": purchases.monthly_total(current_month, kind="expense"),
    }
    with content:
        ui.add_body_html(
            f"<script>window.miraiActuals={json.dumps(actuals)};</script>"
        )
        ui.html(
            r'''
<div id="mirai-app">
  <section class="mk-card input-card">
    <div class="mk-head"><div><small>SIMULATION</small><h2>月間の利益を試算</h2></div><button id="save-plan">計画を保存</button></div>
    <div class="view-switch"><button id="view-simulation" class="active">計画シミュレーション</button><button id="view-provisional">暫定実績</button></div>
    <div id="view-note" class="view-note simulation">入力した計画値で「こうなったら利益はいくら残るか」を試算しています。</div>
    <div id="plan-fields" class="input-grid">
      <label>売上高<input id="sales" inputmode="numeric" value="3000000"></label>
      <div class="dual-plan-field">
        <div class="dual-plan-head"><span>売上原価</span><select id="cogs-mode"><option value="rate">比率で入力</option><option value="amount">金額で入力</option></select></div>
        <div class="dual-plan-inputs"><label>金額<input id="cogs" inputmode="numeric" value="900000"></label><label>売上比率（%）<input id="cogs-rate" inputmode="decimal" value="30"></label></div>
      </div>
      <div class="dual-plan-field">
        <div class="dual-plan-head"><span>人件費</span><select id="personnel-mode"><option value="rate">比率で入力</option><option value="amount">金額で入力</option></select></div>
        <div class="dual-plan-inputs"><label>金額<input id="personnel" inputmode="numeric" value="750000"></label><label>売上比率（%）<input id="personnel-rate" inputmode="decimal" value="25"></label></div>
      </div>
      <label>家賃<input id="rent" inputmode="numeric" value="200000"></label>
      <label>水道光熱費<input id="utilities" inputmode="numeric" value="100000"></label>
      <label>広告費<input id="advertising" inputmode="numeric" value="50000"></label>
      <label>その他管理費<input id="other-expenses" inputmode="numeric" value="50000"></label>
      <label>営業外収益<input id="non-op-income" inputmode="numeric" value="0"></label>
      <label>営業外費用・支払利息<input id="non-op-expense" inputmode="numeric" value="50000"></label>
      <label>目標経常利益<input id="target-profit" inputmode="numeric" value="700000"></label>
      <div class="target-settings"><div class="target-title"><strong>経営目標</strong><span>超過判定はここで変更できます</span></div><div class="target-grid">
        <label>目標原価率（%）<input id="target-cogs-rate" inputmode="decimal" value="30"></label>
        <label>目標労働分配率（%）<input id="target-personnel-rate" inputmode="decimal" value="35"></label>
        <label>目標家賃比率（%）<input id="target-rent-rate" inputmode="decimal" value="10"></label>
        <label>目標光熱費率（%）<input id="target-utilities-rate" inputmode="decimal" value="5"></label>
        <label>目標広告費率（%）<input id="target-advertising-rate" inputmode="decimal" value="5"></label>
        <label>目標営業利益率（%）<input id="target-operating-rate" inputmode="decimal" value="10"></label>
      </div><p class="target-help">労働分配率は「人件費 ÷ 粗利」で判定します。計画入力の「売上比率」とは別の指標です。</p></div>
    </div>
  </section>

  <section class="mk-card result-card">
    <div class="mk-head"><div><small>PROFIT STRUCTURE</small><h2>利益ブロック図</h2></div><span>月間</span></div>
    <p class="block-guide">売上を「原価と粗利」に分け、粗利が「人件費・経費・利益」にどう分かれるかを面積で表示します。</p>
    <div id="profit-summary" class="summary-grid"></div>
    <div id="diagnosis" class="diagnosis"></div>
    <div id="profit-map" class="box-map" aria-label="売上から費用を差し引いて利益が残る流れを表した図"></div>
    <div id="block-legend" class="block-legend"></div>
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
#mirai-app{width:100%;display:grid;gap:16px}.mk-card{background:#fff;border:1px solid #E5E9E6;border-radius:24px;padding:22px;box-shadow:0 8px 24px rgba(39,55,45,.055)}.mk-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.mk-head small{color:#4F7C68;font-weight:800;letter-spacing:.14em}.mk-head h2{font-size:19px;margin:3px 0 0}.mk-head span{color:#7A867F;font-size:11px}.mk-head button{border:0;border-radius:10px;background:#EDF5F0;color:#39745A;padding:9px 14px;font-weight:700}.block-guide{margin:-8px 0 14px;color:#748078;font-size:11px;line-height:1.6}.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.input-grid label{color:#68746D;font-size:10px;font-weight:700}.input-grid input{width:100%;box-sizing:border-box;margin-top:5px;border:1px solid #DDE3DF;border-radius:10px;padding:10px;font-size:14px;outline:none}.input-grid input:focus{border-color:#4F7C68;box-shadow:0 0 0 3px rgba(79,124,104,.1)}.dual-plan-field{border:1px solid #DDE3DF;border-radius:13px;padding:10px;background:#FAFBFA}.dual-plan-head{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#68746D;font-size:11px;font-weight:800}.dual-plan-head select{border:1px solid #DDE3DF;border-radius:8px;background:#fff;padding:6px;color:#39745A;font-size:10px;font-weight:700}.dual-plan-inputs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:7px}.dual-plan-inputs input:disabled{background:#EFF2F0;color:#68746D}.target-settings{grid-column:1/-1;border:1px solid #DDE3DF;border-radius:13px;padding:10px;background:#FAFBFA}.target-settings summary{cursor:pointer;color:#39745A;font-size:11px;font-weight:800}.target-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}.summary{background:#F5F8F6;border-radius:12px;padding:12px}.summary small{display:block;color:#748078;font-size:9px}.summary b{display:block;margin-top:3px;font-size:15px}.summary.negative b{color:#C84B45}.answer{margin-top:18px;border-radius:15px;background:#EAF1FF;padding:16px;color:#244F89}.answer small{display:block;font-size:10px}.answer b{display:block;font-size:22px;margin-top:3px}.answer span{font-size:11px}.compact{margin-bottom:18px}.cash-flow{display:grid;gap:7px}.cash-line{display:grid;grid-template-columns:1fr auto;gap:10px;padding:10px 0;border-bottom:1px solid #EEF0EE;font-size:12px}.cash-line strong{font-size:14px}.cash-line.final{border:0;border-radius:12px;background:#F3F6F4;padding:14px}.cash-line.final strong.negative{color:#C84B45}@media(max-width:520px){.mk-card{padding:18px 15px}.input-grid{grid-template-columns:1fr}.summary-grid{grid-template-columns:1fr 1fr}.target-grid{grid-template-columns:1fr 1fr}}
.view-switch{display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#EEF2EF;padding:5px;border-radius:13px;margin-bottom:10px}.view-switch button{border:0;border-radius:9px;background:transparent;padding:9px 5px;color:#718078;font-size:10px;font-weight:800}.view-switch button.active{background:#fff;color:#39745A;box-shadow:0 2px 8px rgba(39,55,45,.08)}.view-note{border-radius:11px;padding:10px 12px;margin-bottom:14px;font-size:10px;line-height:1.55}.view-note.simulation{background:#EAF1FF;color:#315A91}.view-note.provisional{background:#FFF2DB;color:#855D20}.diagnosis{margin-bottom:12px}.diagnosis-main{border-radius:14px;padding:12px;background:#FFF0ED;color:#8E3F38;font-size:11px;font-weight:800}.diagnosis-main.good{background:#EAF5EE;color:#39745A}.house-map{background:#F3F6F4;border-radius:18px;padding:12px}.house-map svg{display:block;width:100%;height:auto;overflow:visible}.house-part{transition:all .3s ease}.house-legend{display:grid;gap:7px;margin-top:12px}.legend-row{display:grid;grid-template-columns:12px 1fr auto;gap:8px;align-items:center;border-bottom:1px solid #EEF0EE;padding:7px 2px;font-size:10px}.legend-color{width:12px;height:12px;border-radius:3px}.legend-row span{color:#66736C}.legend-row strong{text-align:right}.legend-row small{display:block;color:#89938E}.legend-row.warning strong,.legend-row.warning small{color:#C84B45}.legend-row.warning{background:#FFF7F5;border-radius:8px;padding:7px}.house-caption{text-align:center;color:#748078;font-size:9px;margin-top:6px}
.target-settings{border:2px solid #BFD5C9;background:#F4F9F6;padding:14px;border-radius:16px}.target-title{display:flex;justify-content:space-between;gap:8px;align-items:center;color:#285C45;font-size:12px}.target-title span{font-size:9px;color:#708078}.target-help{margin:10px 0 0;color:#66736C;font-size:9px;line-height:1.55}.house-status{text-align:center;margin-top:7px;font-size:11px;font-weight:900}.house-status.strong{color:#39745A}.house-status.caution{color:#B77822}.house-status.danger{color:#C84B45}
.box-map{height:380px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;background:#E8ECE9;padding:5px;border-radius:16px;overflow:hidden}.box-column{min-width:0;height:100%;display:flex;flex-direction:column;gap:5px}.box-spacer{min-height:0}.money-box{min-height:18px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;border-radius:9px;padding:4px;box-sizing:border-box;overflow:hidden;color:#fff}.money-box span{font-size:10px;font-weight:800;line-height:1.2}.money-box b{font-size:12px;margin-top:2px;white-space:nowrap}.money-box em{font-size:8px;font-style:normal;margin-top:2px;opacity:.9;white-space:nowrap}.box-sales{height:100%;background:#355F4C}.box-cost{background:#82988D}.box-gross{background:#4F8C70}.box-personnel{background:#4A9FD0}.box-rent{background:#8172B5}.box-utilities{background:#4CB7B4}.box-advertising{background:#D8943C}.box-other{background:#99A29D}.box-profit{background:#4B77B7}.box-loss{background:#C85C57}.block-legend{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:12px}.block-legend div{display:flex;justify-content:space-between;gap:6px;padding:7px 9px;background:#F6F8F6;border-radius:8px;font-size:9px}.block-legend i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}.block-legend strong{white-space:nowrap}@media(max-width:520px){.box-map{height:330px;gap:3px;padding:3px}.box-column{gap:3px}.money-box{padding:2px}.money-box span{font-size:8px}.money-box b{font-size:9px}.money-box em{display:none}}
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
    const $=id=>document.getElementById(id), ids=['sales','cogs','cogs-rate','personnel','personnel-rate','rent','utilities','advertising','other-expenses','non-op-income','non-op-expense','target-profit','target-cogs-rate','target-personnel-rate','target-rent-rate','target-utilities-rate','target-advertising-rate','target-operating-rate','consumption-tax','corporate-tax','loan-payment','investment'], modes=['cogs-mode','personnel-mode'];
    const num=id=>Math.max(0,Number(String($(id).value).replace(/,/g,''))||0), yen=n=>new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(n||0);
    function box(label,value,share,cls,note=''){const safe=Math.max(.015,Math.abs(share));return `<div class="money-box ${cls}" style="flex:${safe}"><span>${label}</span>${safe>=.07?`<b>${yen(value)}</b>`:''}${note&&safe>=.11?`<em>${note}</em>`:''}</div>`}
    function legend(label,value,rate,color){return `<div><span><i style="background:${color}"></i>${label}　${(rate*100).toFixed(1)}%</span><strong>${yen(value)}</strong></div>`}
    function syncPlanField(name){
      const mode=$(`${name}-mode`).value,sales=num('sales'),amount=$(name),rate=$(`${name}-rate`);
      if(mode==='rate'){amount.value=Math.round(sales*(Math.max(0,Number(rate.value)||0)/100));amount.disabled=true;rate.disabled=false}
      else{rate.value=sales?((num(name)/sales)*100).toFixed(1):0;amount.disabled=false;rate.disabled=true}
    }
    function syncPlan(){syncPlanField('cogs');syncPlanField('personnel')}
    function update(){
      const sales=num('sales'),cogs=num('cogs'),personnel=num('personnel'),rent=num('rent'),utilities=num('utilities'),advertising=num('advertising'),otherExpenses=num('other-expenses'),otherSga=rent+utilities+advertising+otherExpenses,sga=personnel+otherSga,noi=num('non-op-income'),noe=num('non-op-expense'),target=num('target-profit');
      const gross=sales-cogs,operating=gross-sga,ordinary=operating+noi-noe,rate=sales?cogs/sales:0,required=(1-rate)>0?(sga+noe-noi+target)/(1-rate):0;
      $('profit-summary').innerHTML=[['粗利',gross],['営業利益',operating],['経常利益',ordinary]].map(x=>`<div class="summary ${x[1]<0?'negative':''}"><small>${x[0]}</small><b>${yen(x[1])}</b></div>`).join('');
      const base=Math.max(sales,1),costShare=Math.min(cogs/base,1),grossShare=gross/base,profitShare=operating/base;
      const pct=n=>`${(n*100).toFixed(1)}%`, laborShare=gross>0?personnel/gross:0;
      const personnelShare=personnel/base,rentShare=rent/base,utilitiesShare=utilities/base,advertisingShare=advertising/base,otherShare=otherExpenses/base,visibleProfitShare=Math.max(Math.abs(profitShare),.015);
      $('profit-map').innerHTML=`<div class="box-column">${box('売上',sales,1,'box-sales','100%')}</div><div class="box-column">${box('仕入れ・原価',cogs,costShare,'box-cost',`原価率 ${pct(costShare)}`)}${box(gross<0?'粗利損失':'粗利',gross,Math.max(Math.abs(grossShare),.015),gross<0?'box-loss':'box-gross',`粗利率 ${pct(grossShare)}`)}</div><div class="box-column"><div class="box-spacer" style="flex:${Math.max(costShare,0)}"></div>${box('人件費',personnel,personnelShare,'box-personnel',`分配率 ${pct(laborShare)}`)}${box('家賃',rent,rentShare,'box-rent')}${box('光熱費',utilities,utilitiesShare,'box-utilities')}${box('広告費',advertising,advertisingShare,'box-advertising')}${box('その他',otherExpenses,otherShare,'box-other')}${box(operating<0?'営業損失':'営業利益',Math.abs(operating),visibleProfitShare,operating<0?'box-loss':'box-profit',`利益率 ${pct(profitShare)}`)}</div>`;
      $('block-legend').innerHTML=legend('原価',cogs,costShare,'#82988D')+legend('人件費',personnel,personnelShare,'#4A9FD0')+legend('家賃',rent,rentShare,'#8172B5')+legend('水道光熱費',utilities,utilitiesShare,'#4CB7B4')+legend('広告費',advertising,advertisingShare,'#D8943C')+legend('その他管理費',otherExpenses,otherShare,'#99A29D')+legend(operating<0?'営業損失':'営業利益',operating,profitShare,operating<0?'#C85C57':'#4B77B7');
      const issues=[{label:'原価率',diff:costShare*100-num('target-cogs-rate')},{label:'労働分配率',diff:laborShare*100-num('target-personnel-rate')},{label:'家賃比率',diff:rent/base*100-num('target-rent-rate')},{label:'水道光熱費率',diff:utilities/base*100-num('target-utilities-rate')},{label:'広告費率',diff:advertising/base*100-num('target-advertising-rate')}].filter(x=>x.diff>0);
      const profitGap=num('target-operating-rate')-profitShare*100;if(profitGap>0)issues.push({label:'営業利益率',diff:profitGap});issues.sort((a,b)=>b.diff-a.diff);
      $('diagnosis').innerHTML=issues.length?`<div class="diagnosis-main">⚠️ 最優先で確認：${issues[0].label}（目標との差 ${issues[0].diff.toFixed(1)}ポイント）</div>`:`<div class="diagnosis-main good">✓ 設定した目標比率の範囲内です</div>`;
      const gap=Math.max(0,required-sales);$('sales-answer').innerHTML=`<small>目標経常利益 ${yen(target)} に必要な売上</small><b>${yen(required)}</b><span>${gap>0?`現在の計画より ${yen(gap)} 増やす必要があります`:'現在の売上計画で達成圏内です'}</span>`;
      const ct=num('consumption-tax'),corp=num('corporate-tax'),loan=num('loan-payment'),inv=num('investment'),cash=ordinary-corp-ct-loan-inv;
      $('cash-flow').innerHTML=`<div class="cash-line"><span>経常利益からスタート</span><strong>${yen(ordinary)}</strong></div><div class="cash-line"><span>税金の支払</span><strong>− ${yen(ct+corp)}</strong></div><div class="cash-line"><span>借入元金・設備投資</span><strong>− ${yen(loan+inv)}</strong></div><div class="cash-line final"><span>手元資金の増減目安</span><strong class="${cash<0?'negative':''}">${yen(cash)}</strong></div>`;
    }
    ids.filter(id=>!['sales','cogs','cogs-rate','personnel','personnel-rate'].includes(id)).forEach(id=>$(id).addEventListener('input',update));
    $('sales').addEventListener('input',()=>{syncPlan();update()});
    ['cogs','personnel'].forEach(id=>$(id).addEventListener('input',()=>{if($(`${id}-mode`).value==='amount')syncPlanField(id);update()}));
    ['cogs-rate','personnel-rate'].forEach(id=>$(id).addEventListener('input',()=>{const name=id.replace('-rate','');if($(`${name}-mode`).value==='rate')syncPlanField(name);update()}));
    modes.forEach(id=>$(id).addEventListener('change',()=>{syncPlan();update()}));
    try{const saved=JSON.parse(localStorage.getItem('habitory-future-plan')||'null');if(saved){ids.forEach(id=>{if(saved[id]!==undefined)$(id).value=saved[id]});modes.forEach(id=>{if(saved[id]!==undefined)$(id).value=saved[id]});if(saved['cogs-mode']===undefined)$('cogs-mode').value='amount';if(saved['personnel-mode']===undefined)$('personnel-mode').value='amount';if(saved['target-personnel-basis']!=='gross-profit')$('target-personnel-rate').value=35;if(saved['other-expenses']===undefined&&saved['other-sga']!==undefined){$('rent').value=0;$('utilities').value=0;$('advertising').value=0;$('other-expenses').value=saved['other-sga']}if(saved.sga!==undefined&&saved.personnel===undefined){$('personnel').value=Math.round(saved.sga*.65);$('other-expenses').value=Math.round(saved.sga*.35)}}}catch(e){}
    $('save-plan').onclick=()=>{const data={'target-personnel-basis':'gross-profit'};[...ids,...modes].forEach(id=>data[id]=$(id).value);localStorage.setItem('habitory-future-plan',JSON.stringify(data));$('save-plan').textContent='保存しました';setTimeout(()=>$('save-plan').textContent='計画を保存',1400)};
    let simulationData=null;
    function setView(mode){
      const provisional=mode==='provisional',fields=$('plan-fields').querySelectorAll('input,select');
      if(provisional){
        simulationData={};[...ids,...modes].forEach(id=>simulationData[id]=$(id).value);
        const actual=window.miraiActuals||{};$('sales').value=actual.sales||0;$('cogs').value=actual.cogs||0;$('cogs-mode').value='amount';$('personnel').value=0;$('personnel-mode').value='amount';$('rent').value=0;$('utilities').value=0;$('advertising').value=0;$('other-expenses').value=actual.other||0;$('non-op-income').value=0;$('non-op-expense').value=0;
        fields.forEach(field=>field.disabled=true);$('save-plan').disabled=true;$('view-note').className='view-note provisional';$('view-note').textContent='暫定実績：売上・仕入れ・その他経費は実績です。人件費など未入力の項目は0円のため、確定利益ではありません。';
      }else{
        if(simulationData){[...ids,...modes].forEach(id=>{if(simulationData[id]!==undefined)$(id).value=simulationData[id]})}
        fields.forEach(field=>field.disabled=false);$('save-plan').disabled=false;$('view-note').className='view-note simulation';$('view-note').textContent='入力した計画値で「こうなったら利益はいくら残るか」を試算しています。';syncPlan();
      }
      $('view-simulation').classList.toggle('active',!provisional);$('view-provisional').classList.toggle('active',provisional);update();
    }
    $('view-simulation').onclick=()=>setView('simulation');$('view-provisional').onclick=()=>setView('provisional');
    syncPlan();update();
  }
  init();
})();
</script>
            '''
        )
