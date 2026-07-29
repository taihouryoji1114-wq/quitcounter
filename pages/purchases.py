from nicegui import ui

from core.auth import require_login
from core.theme import Theme


@ui.page("/shiire")
def purchases():
    if not require_login():
        return
    Theme.page("仕入れノート")
    ui.add_head_html(
        '<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>'
    )
    content = Theme.shell(
        "仕入れノート",
        "納品書を撮って、商品と金額を記録",
        back_to="/",
    )
    with content:
        ui.html(
            r'''
<div id="shiire-app">
  <section id="capture-card" class="s-card">
    <div class="privacy-badge">端末内だけで処理</div>
    <div class="camera-symbol">▣</div>
    <h2>納品書を撮る</h2>
    <p>写真一覧にはアクセスしません。アプリ内カメラだけを使います。</p>
    <button id="open-camera" class="primary-action">カメラを開く</button>
    <small>画像は保存・送信されず、読取後に破棄されます</small>
  </section>

  <section id="review-card" class="s-card hidden">
    <div class="review-title">
      <div><b>読み取り結果</b><span id="read-status">内容をご確認ください</span></div>
      <button id="retake" class="text-action">撮り直す</button>
    </div>
    <div class="field-grid">
      <label>仕入先<input id="supplier" placeholder="仕入先名"></label>
      <label>納品日<input id="delivery-date" type="date"></label>
    </div>
    <div class="items-head"><span>商品名</span><span>数量</span><span>単価</span></div>
    <div id="items"></div>
    <button id="add-item" class="text-action add-line">＋ 商品を追加</button>
    <div class="total-line"><span>合計</span><strong id="total">¥0</strong></div>
    <button id="save-purchase" class="primary-action full">仕入帳に登録する</button>
  </section>

  <section class="history-section">
    <div class="history-title"><div><small>RECENT</small><h2>最近の仕入れ</h2></div><button id="clear-history">記録を消去</button></div>
    <div id="history"></div>
  </section>
</div>

<div id="camera-modal" class="camera-modal hidden">
  <div class="camera-top"><button id="close-camera">×</button><b>納品書を枠に合わせてください</b><span></span></div>
  <div class="camera-view"><video id="camera-video" autoplay playsinline muted></video><div class="doc-frame"></div></div>
  <div class="camera-bottom"><p>写真は端末に保存されません</p><button id="shutter" aria-label="撮影"><span></span></button></div>
</div>

<div id="reading" class="reading hidden"><div class="loader"></div><b id="progress">文字を読み取っています 0%</b><small>初回は読取準備に少し時間がかかります</small></div>
<div id="notice" class="notice hidden"></div>

<style>
#shiire-app{width:100%}.s-card{background:#fff;border:1px solid #E5E9E6;border-radius:24px;padding:26px 22px;box-shadow:0 8px 24px rgba(39,55,45,.055)}
#capture-card{text-align:center;min-height:330px;display:flex;flex-direction:column;align-items:center;justify-content:center}.privacy-badge{background:#EAF7F0;color:#39745A;border-radius:999px;padding:6px 12px;font-size:11px;font-weight:700}.camera-symbol{width:62px;height:54px;display:grid;place-items:center;margin:20px 0 10px;border-radius:15px;background:#EAF1FF;color:#246BFD;font-size:30px}#capture-card h2{font-size:22px;margin:0}#capture-card p{color:#6D7872;font-size:13px;margin:8px 0 18px;max-width:360px}.primary-action{border:0;border-radius:14px;background:#246BFD;color:#fff;padding:13px 25px;font-weight:700;box-shadow:0 8px 18px rgba(36,107,253,.2)}#capture-card small{color:#89938D;font-size:10px;margin-top:14px}.hidden{display:none!important}
.review-title,.history-title{display:flex;justify-content:space-between;align-items:center}.review-title>div{display:flex;flex-direction:column}.review-title b{font-size:18px}.review-title span{font-size:11px;color:#78827C;margin-top:4px}.text-action,#clear-history{border:0;background:transparent;color:#246BFD;font-weight:700;font-size:12px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:22px 0}.field-grid label{font-size:10px;color:#69756E;font-weight:700}.field-grid input,.item-row input{width:100%;box-sizing:border-box;border:1px solid #DDE3DF;border-radius:10px;padding:10px;margin-top:6px;outline:none}.field-grid input:focus,.item-row input:focus{border-color:#246BFD;box-shadow:0 0 0 3px rgba(36,107,253,.08)}.items-head,.item-row{display:grid;grid-template-columns:1.7fr .55fr .7fr 28px;gap:8px;align-items:center}.items-head{color:#8A948E;background:#F7F8F7;border-radius:8px;padding:8px 9px;font-size:9px;font-weight:700}.item-row{padding:8px 0;border-bottom:1px solid #EEF0EE}.item-row input{margin:0;font-size:12px}.remove-item{border:0;background:transparent;color:#9AA39E;font-size:20px}.add-line{padding:12px 0}.total-line{display:flex;justify-content:space-between;border-top:1px solid #DDE3DF;margin-top:8px;padding:16px 0;font-size:16px}.total-line strong{font-size:22px}.full{width:100%}.history-section{margin-top:34px}.history-title small{color:#4F7C68;letter-spacing:.16em;font-weight:800}.history-title h2{margin:3px 0 0;font-size:19px}#clear-history{color:#909994}.history-card{display:grid;grid-template-columns:1fr auto;gap:5px;margin-top:10px;background:#fff;border:1px solid #E5E9E6;border-radius:15px;padding:15px}.history-card b{font-size:13px}.history-card small{color:#84908A}.history-card strong{grid-row:1/3;grid-column:2;align-self:center}.empty-history{color:#8A948E;text-align:center;background:#fff;border:1px dashed #DDE3DF;border-radius:15px;padding:24px;margin-top:10px;font-size:12px}
.camera-modal{position:fixed;inset:0;z-index:9999;background:#05070A;color:#fff;display:grid;grid-template-rows:64px 1fr 140px}.camera-top{display:grid;grid-template-columns:48px 1fr 48px;align-items:center;text-align:center;padding:0 14px}.camera-top button{width:40px;height:40px;border:0;border-radius:50%;background:#ffffff22;color:#fff;font-size:26px}.camera-top b{font-size:13px}.camera-view{position:relative;overflow:hidden;background:#111}.camera-view video{width:100%;height:100%;object-fit:cover}.doc-frame{position:absolute;inset:7%;border:3px solid #fff;border-radius:10px;box-shadow:0 0 0 9999px #00000055}.camera-bottom{display:flex;flex-direction:column;align-items:center;justify-content:center}.camera-bottom p{font-size:10px;color:#B5BEC9;margin:0 0 12px}#shutter{width:70px;height:70px;display:grid;place-items:center;border:3px solid #fff;border-radius:50%;background:transparent}#shutter span{width:56px;height:56px;border-radius:50%;background:#fff}.reading{position:fixed;inset:0;z-index:10000;background:#14243EEE;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}.loader{width:48px;height:48px;border:4px solid #ffffff44;border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite}.reading b{margin-top:16px}.reading small{margin-top:7px;color:#D8E1ED}@keyframes spin{to{transform:rotate(360deg)}}.notice{position:fixed;left:50%;bottom:24px;z-index:10001;transform:translateX(-50%);background:#193529;color:#fff;border-radius:12px;padding:12px 18px;font-size:12px;box-shadow:0 10px 30px #0003;white-space:nowrap}
@media(max-width:520px){.field-grid{grid-template-columns:1fr}.s-card{padding:22px 16px}.items-head,.item-row{grid-template-columns:1.45fr .52fr .67fr 24px}}
</style>
            ''',
            sanitize=False,
        ).classes("w-full")
        ui.add_body_html(
            r'''
<script>
(() => {
  const $=id=>document.getElementById(id), yen=n=>new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(n||0);
  let stream=null, rows=[];
  const today=new Date(); $('delivery-date').value=`${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
  function notify(msg){$('notice').textContent=msg;$('notice').classList.remove('hidden');setTimeout(()=>$('notice').classList.add('hidden'),2400)}
  function total(){const value=rows.reduce((s,r)=>s+(Number(r.qty)||0)*(Number(r.price)||0),0);$('total').textContent=yen(value);return value}
  function renderRows(){const root=$('items');root.innerHTML='';rows.forEach((r,i)=>{const line=document.createElement('div');line.className='item-row';line.innerHTML=`<input aria-label="商品名" placeholder="商品名" value="${String(r.name||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;')}"><input aria-label="数量" inputmode="decimal" value="${r.qty||1}"><input aria-label="単価" inputmode="numeric" value="${r.price||0}"><button class="remove-item" aria-label="削除">×</button>`;const inputs=line.querySelectorAll('input');inputs[0].oninput=e=>rows[i].name=e.target.value;inputs[1].oninput=e=>{rows[i].qty=Number(e.target.value);total()};inputs[2].oninput=e=>{rows[i].price=Number(e.target.value);total()};line.querySelector('button').onclick=()=>{rows.splice(i,1);renderRows()};root.appendChild(line)});total()}
  function parseText(text){const lines=text.split(/\r?\n/).map(x=>x.replace(/[|｜]/g,' ').replace(/\s+/g,' ').trim()).filter(x=>x.length>1);const supplier=lines.find(x=>/(株式会社|有限会社|商店|市場|フーズ|食品|青果|乳業)/.test(x)&&!/(御中|様|納品先)/.test(x));if(supplier)$('supplier').value=supplier;const dm=text.match(/(20\d{2})[年\/\-.]\s*(\d{1,2})[月\/\-.]\s*(\d{1,2})/);if(dm)$('delivery-date').value=`${dm[1]}-${dm[2].padStart(2,'0')}-${dm[3].padStart(2,'0')}`;const found=[];for(const line of lines){const nums=[...line.matchAll(/(?:¥|￥)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)/g)];if(nums.length<2||!/[ぁ-んァ-ヶ一-龠]/.test(line)||/(小計|合計|消費税|税率|請求|納品書|電話|登録番号)/.test(line))continue;const q=nums.length>=3?nums[nums.length-3]:nums[nums.length-2],p=nums.length>=3?nums[nums.length-2]:null,a=Number(nums[nums.length-1][1].replace(/,/g,'')),qty=Number(q[1].replace(/,/g,''));const name=line.slice(0,q.index).replace(/^[0-9０-９\-–—.\s]+/,'').trim();if(!name||!qty)continue;found.push({name,qty,price:p?Number(p[1].replace(/,/g,'')):Math.round(a/qty)})}return found.slice(0,30)}
  async function openCamera(){try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});$('camera-video').srcObject=stream;$('camera-modal').classList.remove('hidden')}catch(e){notify('カメラの使用を許可してください')}}
  function closeCamera(){if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;$('camera-video').srcObject=null;$('camera-modal').classList.add('hidden')}
  async function capture(){const v=$('camera-video');if(!v.videoWidth)return;const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0,c.width,c.height);closeCamera();$('reading').classList.remove('hidden');try{const worker=await Tesseract.createWorker('jpn+eng',1,{logger:m=>{if(m.status==='recognizing text')$('progress').textContent=`文字を読み取っています ${Math.round(m.progress*100)}%`}});const result=await worker.recognize(c);await worker.terminate();rows=parseText(result.data.text);if(!rows.length)rows=[{name:'',qty:1,price:0}];$('read-status').textContent=rows[0].name?`${rows.length}件の候補を読み取りました`:'明細を判定できませんでした。入力してください';renderRows();$('capture-card').classList.add('hidden');$('review-card').classList.remove('hidden')}catch(e){rows=[{name:'',qty:1,price:0}];renderRows();$('read-status').textContent='読取ができませんでした。入力してください';$('capture-card').classList.add('hidden');$('review-card').classList.remove('hidden')}finally{c.width=1;c.height=1;$('reading').classList.add('hidden')}}
  function history(){let data=[];try{data=JSON.parse(localStorage.getItem('habitory-purchases')||'[]')}catch(e){}const root=$('history');root.innerHTML=data.length?'':'<div class="empty-history">まだ記録がありません</div>';data.slice(0,12).forEach(x=>{const d=document.createElement('div');d.className='history-card';d.innerHTML=`<b>${x.supplier}</b><small>${x.date} ・ ${x.count}品</small><strong>${yen(x.total)}</strong>`;root.appendChild(d)})}
  $('open-camera').onclick=openCamera;$('close-camera').onclick=closeCamera;$('shutter').onclick=capture;$('retake').onclick=()=>{$('review-card').classList.add('hidden');$('capture-card').classList.remove('hidden')};$('add-item').onclick=()=>{rows.push({name:'',qty:1,price:0});renderRows()};$('save-purchase').onclick=()=>{const record={id:Date.now(),supplier:$('supplier').value.trim()||'仕入先未入力',date:$('delivery-date').value,count:rows.length,total:total(),items:rows};let data=[];try{data=JSON.parse(localStorage.getItem('habitory-purchases')||'[]')}catch(e){}data.unshift(record);localStorage.setItem('habitory-purchases',JSON.stringify(data));history();notify('仕入帳に登録しました');$('review-card').classList.add('hidden');$('capture-card').classList.remove('hidden')};$('clear-history').onclick=()=>{if(confirm('この端末の仕入れ記録をすべて消去しますか？')){localStorage.removeItem('habitory-purchases');history()}};history();
})();
</script>
            '''
        )
