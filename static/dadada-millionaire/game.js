(()=>{'use strict';
const KEY='dadada-millionaire-v1';
const businesses=[
 {id:'stall',name:'屋台ちゃんこ',icon:'🍲',desc:'あなたの伝説は一台の屋台から始まる',base:120,income:2,unlock:0},
 {id:'shop',name:'下町食堂',icon:'🏮',desc:'常連でにぎわう最初の実店舗',base:950,income:14,unlock:300},
 {id:'cafe',name:'駅前カフェ',icon:'☕',desc:'若者が集まる人気の二号店',base:7200,income:88,unlock:3000},
 {id:'restaurant',name:'高級レストラン',icon:'🍽️',desc:'予約の取れない街の名店',base:52000,income:610,unlock:25000},
 {id:'hotel',name:'シティホテル',icon:'🏨',desc:'食と宿泊をまとめた大型事業',base:380000,income:4300,unlock:160000},
 {id:'tower',name:'大富豪タワー',icon:'🌆',desc:'街の夜景を変える本社ビル',base:2800000,income:32000,unlock:1200000},
 {id:'group',name:'全国飲食グループ',icon:'🗾',desc:'全国の味と雇用を動かす企業へ',base:21000000,income:250000,unlock:9000000},
 {id:'space',name:'宇宙都市事業',icon:'🚀',desc:'ついに商圏は地球を飛び出す',base:180000000,income:2200000,unlock:75000000}
];
const properties=[
 {id:'room',name:'ワンルーム投資',icon:'🏠',desc:'小さく始める家賃収入',base:3500,income:25,unlock:1500},
 {id:'apartment',name:'木造アパート',icon:'🏘️',desc:'地域に根づく安定した住まい',base:28000,income:180,unlock:12000},
 {id:'mansion',name:'駅前マンション',icon:'🏢',desc:'利便性の高い人気物件',base:210000,income:1350,unlock:85000},
 {id:'building',name:'商業ビル',icon:'🏬',desc:'テナント収入で街を支配',base:1600000,income:9800,unlock:650000},
 {id:'resort',name:'海辺のリゾート',icon:'🏝️',desc:'憧れと収益を同時に手にする',base:12500000,income:78000,unlock:5000000}
];
const life=[
 {id:'shirt',cat:'服',name:'仕立ての良いジャケット',icon:'🧥',cost:800,bonus:5},
 {id:'sofa',cat:'家具',name:'本革のソファ',icon:'🛋️',cost:2800,bonus:8},
 {id:'watch',cat:'服',name:'大富豪の腕時計',icon:'⌚',cost:9000,bonus:12},
 {id:'compact',cat:'車',name:'小さな愛車',icon:'🚗',cost:26000,bonus:18},
 {id:'condo',cat:'家',name:'都心のマンション',icon:'🏙️',cost:85000,bonus:25},
 {id:'sports',cat:'車',name:'真紅のスポーツカー',icon:'🏎️',cost:280000,bonus:38},
 {id:'villa',cat:'家',name:'庭付きの豪邸',icon:'🏡',cost:750000,bonus:55},
 {id:'art',cat:'家具',name:'世界に一つの名画',icon:'🖼️',cost:2200000,bonus:80},
 {id:'jet',cat:'車',name:'プライベートジェット',icon:'🛩️',cost:9000000,bonus:130},
 {id:'castle',cat:'家',name:'黄金の迎賓館',icon:'🏰',cost:35000000,bonus:200}
];
const markets=[
 {id:'food',name:'フード株',icon:'🍜',risk:.12,rate:.18,min:500},
 {id:'tech',name:'未来テック',icon:'🤖',risk:.28,rate:.42,min:2500},
 {id:'land',name:'都市開発',icon:'🏗️',risk:.2,rate:.3,min:12000},
 {id:'venture',name:'新興企業',icon:'💡',risk:.44,rate:.75,min:60000}
];
const defaults={cash:100,taps:0,earned:100,spent:0,business:{},property:{},owned:[],last:Date.now(),sound:true,marketSeed:0,marketMood:1,lifeCat:'すべて',claimed:[]};
let s=load(),combo=1,comboTimer=0,lastTap=0;
const $=q=>document.querySelector(q),fmt=n=>'¥'+Math.floor(n).toLocaleString('ja-JP'),level=(group,id)=>(s[group][id]||0),price=(x,n)=>Math.floor(x.base*Math.pow(1.18,n));
function load(){try{let saved=JSON.parse(localStorage.getItem(KEY)||'{}');return {...defaults,...saved,business:{...(saved.business||{})},property:{...(saved.property||{})}}}catch(e){return {...defaults,business:{},property:{},owned:[],claimed:[]}}}
function save(){s.last=Date.now();localStorage.setItem(KEY,JSON.stringify(s))}
function income(){return businesses.reduce((a,x)=>a+x.income*level('business',x.id),0)+properties.reduce((a,x)=>a+x.income*level('property',x.id),0)}
function bonus(){return s.owned.reduce((a,id)=>a+(life.find(x=>x.id===id)?.bonus||0),0)}
function tapValue(){return Math.max(10,Math.floor((10+income()*.08)*(1+bonus()/100)*combo))}
function worth(){return s.cash+s.spent}
function title(){let w=worth();return w>=1e8?'世界的大富豪':w>=1e7?'財閥総帥':w>=1e6?'街の支配人':w>=1e5?'敏腕経営者':w>=1e4?'若手実業家':w>=1e3?'繁盛店主':'駆け出し店主'}
function district(){let w=worth();return w>=1e8?'世界経済都市':w>=1e7?'黄金メガシティ':w>=1e6?'都心ビジネス街':w>=1e5?'駅前新都心':w>=1e4?'にぎわい商店街':'下町商店街'}
function update(){
 $('#cash').textContent=fmt(s.cash);$('#income').textContent='+'+fmt(income())+'/秒';$('#netWorth').textContent=fmt(worth());$('#rank').textContent=title();$('#district').textContent=district();$('#tapValue').textContent='+'+fmt(tapValue());$('#combo').innerHTML='COMBO <b>×'+combo.toFixed(1)+'</b>';
 let next=businesses.find(x=>worth()<x.unlock);$('#nextGoal').textContent=next?'次の目標：'+next.name+'を解放':'すべての事業を解放！';
}
function card(x,group){let n=level(group,x.id),p=price(x,n),locked=worth()<x.unlock;return `<article class="item-card ${locked?'locked':''} ${n?'owned':''}"><div class="icon">${x.icon}</div><div><h3>${x.name}</h3><p>${locked?fmt(x.unlock)+'の総資産で解放':x.desc}</p><div class="yield">${n?'毎秒 +'+fmt(x.income*n):'毎秒 +'+fmt(x.income)}</div></div><button class="buy" data-buy="${group}:${x.id}" ${locked||s.cash<p?'disabled':''}>${n?'増やす':'購入'}<br>${fmt(p)}</button><span class="level">Lv.${n}</span></article>`}
function renderLists(){
 $('#businessList').innerHTML=businesses.map(x=>card(x,'business')).join('');$('#propertyList').innerHTML=properties.map(x=>card(x,'property')).join('');
 document.querySelectorAll('[data-buy]').forEach(b=>b.onclick=()=>{let [g,id]=b.dataset.buy.split(':'),x=(g==='business'?businesses:properties).find(v=>v.id===id),p=price(x,level(g,id));if(s.cash<p)return;s.cash-=p;s.spent+=p;s[g][id]=level(g,id)+1;beep(420);toast(`${x.name}を${level(g,id)===1?'手に入れた！':'拡大した！'}`);render()});
}
function renderMarket(){let moods=[{h:'追い風のニュース',p:'市場には明るい兆し。利益が出やすい局面です。',m:1.2},{h:'静かな相場',p:'大きな材料はありません。資金配分が重要です。',m:1},{h:'警戒が必要',p:'不安定な値動き。高い利益には相応の危険があります。',m:.78}],news=moods[s.marketMood];$('#marketNews').innerHTML=`<small>MARKET NEWS</small><h3>${news.h}</h3><p>${news.p}</p>`;$('#marketList').innerHTML=markets.map(x=>`<button class="market-card" data-market="${x.id}"><i>${x.icon}</i><b>${x.name}</b><small>危険度 ${Math.round(x.risk*100)}%</small><span>${fmt(x.min)} 投資</span></button>`).join('');document.querySelectorAll('[data-market]').forEach(b=>b.onclick=()=>invest(markets.find(x=>x.id===b.dataset.market)))}
function invest(x){if(s.cash<x.min){toast('資金が足りません');return}let amount=Math.max(x.min,Math.floor(s.cash*.15));s.cash-=amount;s.spent+=amount;let win=Math.random()>x.risk*(1.25-s.marketMood*.2),delta=win?Math.floor(amount*x.rate*s.marketMood):-Math.floor(amount*(.25+x.risk*.5));setTimeout(()=>{s.cash+=amount+delta;s.earned+=Math.max(0,delta);toast(win?`${x.name} 成功！ +${fmt(delta)}`:`${x.name} 下落… ${fmt(delta)}`);s.marketMood=Math.floor(Math.random()*3);render();save()},450);toast(fmt(amount)+'を投資しました');render()}
function renderLife(){let cats=['すべて','家','家具','車','服'];$('#lifeFilter').innerHTML=cats.map(c=>`<button class="${s.lifeCat===c?'active':''}" data-cat="${c}">${c}</button>`).join('');document.querySelectorAll('[data-cat]').forEach(b=>b.onclick=()=>{s.lifeCat=b.dataset.cat;renderLife()});let list=s.lifeCat==='すべて'?life:life.filter(x=>x.cat===s.lifeCat);$('#lifeList').innerHTML=list.map(x=>{let own=s.owned.includes(x.id);return `<article class="item-card ${own?'owned':''}"><div class="icon">${x.icon}</div><div><h3>${x.name}</h3><p>${x.cat}・タップ収益 +${x.bonus}%</p><div class="yield">${own?'所有済み':'夢をかなえる買い物'}</div></div><button class="buy" data-life="${x.id}" ${own||s.cash<x.cost?'disabled':''}>${own?'購入済み':fmt(x.cost)}</button></article>`}).join('');document.querySelectorAll('[data-life]').forEach(b=>b.onclick=()=>{let x=life.find(v=>v.id===b.dataset.life);if(s.cash<x.cost||s.owned.includes(x.id))return;s.cash-=x.cost;s.spent+=x.cost;s.owned.push(x.id);beep(700);toast(`${x.name}を購入！`);render()});let home=[...life].reverse().find(x=>x.cat==='家'&&s.owned.includes(x.id));$('#homeName').textContent=home?home.name:'六畳一間の部屋';$('#lifeBonus').textContent=`タップ収益ボーナス +${bonus()}%`;$('#roomItems').textContent=s.owned.slice(-4).map(id=>life.find(x=>x.id===id)?.icon).join(' ')}
const missions=[{id:'tap100',name:'指が資本',text:'100回タップする',ok:()=>s.taps>=100,reward:1000},{id:'shops5',name:'街の経営者',text:'事業を合計5店舗持つ',ok:()=>Object.values(s.business).reduce((a,b)=>a+b,0)>=5,reward:5000},{id:'home',name:'夢の我が家',text:'初めて家を購入する',ok:()=>life.some(x=>x.cat==='家'&&s.owned.includes(x.id)),reward:12000},{id:'million',name:'百万長者',text:'総資産100万円を超える',ok:()=>worth()>=1e6,reward:100000}];
function renderRecord(){let totalUnits=[...Object.values(s.business),...Object.values(s.property)].reduce((a,b)=>a+b,0);$('#stats').innerHTML=`<div class="stat"><small>累計収益</small><b>${fmt(s.earned)}</b></div><div class="stat"><small>総タップ数</small><b>${s.taps.toLocaleString()}</b></div><div class="stat"><small>所有事業・物件</small><b>${totalUnits}</b></div><div class="stat"><small>購入した宝物</small><b>${s.owned.length}</b></div>`;$('#missions').innerHTML=missions.map(m=>{let done=m.ok(),claimed=s.claimed.includes(m.id);return `<div class="mission ${done?'done':''}" data-mission="${m.id}"><b>${m.name}</b><span>${m.text}</span><em>${claimed?'達成済み':done?'受取 '+fmt(m.reward):'挑戦中'}</em></div>`}).join('');document.querySelectorAll('[data-mission]').forEach(el=>el.onclick=()=>{let m=missions.find(x=>x.id===el.dataset.mission);if(m.ok()&&!s.claimed.includes(m.id)){s.claimed.push(m.id);s.cash+=m.reward;s.earned+=m.reward;toast('報酬 '+fmt(m.reward)+'！');render()}})}
function render(){update();renderLists();renderMarket();renderLife();renderRecord();save()}
function toast(t){let e=$('#toast');e.textContent=t;e.classList.add('show');clearTimeout(e._t);e._t=setTimeout(()=>e.classList.remove('show'),1700)}
function beep(f=520){if(!s.sound)return;try{let a=new(window.AudioContext||window.webkitAudioContext),o=a.createOscillator(),g=a.createGain();o.frequency.value=f;o.type='sine';g.gain.setValueAtTime(.05,a.currentTime);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+.08);o.connect(g);g.connect(a.destination);o.start();o.stop(a.currentTime+.08)}catch(e){}}
function tap(e){let now=Date.now();combo=now-lastTap<430?Math.min(5,combo+.1):1;lastTap=now;clearTimeout(comboTimer);comboTimer=setTimeout(()=>{combo=1;$('#combo').classList.remove('show');update()},900);$('#combo').classList.add('show');let v=tapValue();s.cash+=v;s.earned+=v;s.taps++;let f=document.createElement('span');f.className='floater';f.textContent='+'+fmt(v);let r=$('.city-stage').getBoundingClientRect();f.style.left=((e.clientX||r.left+r.width/2)-r.left-25)+'px';f.style.top=((e.clientY||r.top+r.height*.65)-r.top)+'px';$('#floaters').appendChild(f);setTimeout(()=>f.remove(),850);beep(480+combo*35);update();if(s.taps%10===0){renderLists();renderRecord()}save()}
function begin(){let old=s.last?Date.now()-s.last:0,gain=Math.min(income()*Math.floor(old/1000),income()*14400);$('#splash').style.display='none';$('#app').hidden=false;render();if(gain>=10&&old>60000){s.cash+=gain;s.earned+=gain;$('#offlineCash').textContent='+'+fmt(gain);$('#offlineTime').textContent=`${Math.floor(old/60000)}分ぶんの自動収益`;$('#offline').hidden=false}}
$('#start').onclick=begin;$('#tap').onclick=tap;$('#back').onclick=()=>location.href='/';$('#sound').onclick=()=>{s.sound=!s.sound;$('#sound').textContent=s.sound?'♪':'×';save()};$('#offlineOk').onclick=()=>{$('#offline').hidden=true;render()};$('#reset').onclick=()=>{if(confirm('すべての事業と資産を手放して、最初から始めますか？')){localStorage.removeItem(KEY);location.reload()}};
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button,.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#'+b.dataset.tab).classList.add('active');scrollTo({top:document.querySelector('.tabs').offsetTop,behavior:'smooth'})});
setInterval(()=>{let x=income()/10;if(x){s.cash+=x;s.earned+=x;update()}},100);setInterval(save,5000);addEventListener('pagehide',save);$('#sound').textContent=s.sound?'♪':'×';
})();
