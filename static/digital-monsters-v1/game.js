const $=s=>document.querySelector(s),screens=[...document.querySelectorAll('.screen')];
const names=['イグニス','アクアロ','リーフィ'],positions=['left','center','right'];
const partnerImages=['assets/ignis.png','assets/aquaro.png','assets/leafy.png'];
let partner=Number(localStorage.getItem('codebeasts:partner')||0),enemy=100,ally=100,busy=false,mode='start',encounterCooldown=0;
let experience=Number(localStorage.getItem('codebeasts:exp')||0),party=JSON.parse(localStorage.getItem('codebeasts:party')||'[]');
function show(id){mode=id;screens.forEach(s=>s.classList.toggle('active',s.id===id))}
async function requestLandscape(){
  try{if(document.documentElement.requestFullscreen&&!document.fullscreenElement)await document.documentElement.requestFullscreen()}catch(error){}
  try{if(screen.orientation?.lock)await screen.orientation.lock('landscape')}catch(error){}
}
$('#begin').onclick=async()=>{await requestLandscape();show('choose')};
document.querySelectorAll('[data-pick]').forEach(button=>button.onclick=()=>{
  const picked=Number(button.dataset.pick);
  if(button.classList.contains('selected')){partner=picked;localStorage.setItem('codebeasts:partner',partner);setPartnerArt();show('field');return}
  document.querySelectorAll('[data-pick]').forEach(item=>item.classList.remove('selected'));button.classList.add('selected');
  $('#choose-note').innerHTML=`<b>${names[picked]}</b>を選択中。もう一度タップして決定。`;
});
function currentLevel(){return 5+Math.floor(experience/50)}
function setPartnerArt(){$('#partner img').src=partnerImages[partner];$('#ally-art').src=partnerImages[partner];$('#ally-name').textContent=names[partner]+'　Lv.'+currentLevel()}setPartnerArt();
const pos={x:32,y:62,px:27,py:67,dx:0,dy:0},stick=$('#stick'),nub=$('#stick i');let pid=null;
const obstacles=[[0,0,29,43],[0,68,27,100],[0,43,12,68],[35,0,55,31],[91,0,100,100],[29,0,35,27],[48,27,58,47],[69,0,91,13],[75,82,91,100],[34,86,75,100]];
function blocked(x,y){return obstacles.some(([l,t,r,b])=>x>l&&x<r&&y>t&&y<b)}
function move(event){if(event.pointerId!==pid||mode!=='field')return;const rect=stick.getBoundingClientRect(),x=event.clientX-rect.left-rect.width/2,y=event.clientY-rect.top-rect.height/2,d=Math.hypot(x,y),m=Math.min(35,d),nx=d?x/d:0,ny=d?y/d:0;pos.dx=nx*m/35;pos.dy=ny*m/35;nub.style.transform=`translate(${nx*m}px,${ny*m}px)`}
stick.onpointerdown=event=>{if(mode!=='field')return;pid=event.pointerId;stick.setPointerCapture(pid);move(event)};stick.onpointermove=move;
stick.onpointerup=stick.onpointercancel=event=>{if(event.pointerId!==pid)return;pid=null;pos.dx=pos.dy=0;nub.style.transform='none'};
function loop(){if(mode==='field'){if(encounterCooldown>0)encounterCooldown--;const nx=Math.max(3,Math.min(94,pos.x+pos.dx*.18)),ny=Math.max(9,Math.min(90,pos.y+pos.dy*.25));if(!blocked(nx,pos.y))pos.x=nx;if(!blocked(pos.x,ny))pos.y=ny;pos.px+=(pos.x-5-pos.px)*.045;pos.py+=(pos.y+4-pos.py)*.045;$('#hero').style.left=pos.x+'%';$('#hero').style.top=pos.y+'%';$('#partner').style.left=pos.px+'%';$('#partner').style.top=pos.py+'%';const inGrass=pos.x>58&&pos.x<89&&pos.y>14&&pos.y<80,moving=Math.hypot(pos.dx,pos.dy)>.1;if(inGrass&&moving&&encounterCooldown===0&&Math.random()<.012)startBattle()}requestAnimationFrame(loop)}requestAnimationFrame(loop);
function setHp(id,value){const bar=$(id);bar.style.width=value+'%';bar.classList.toggle('low',value<=50&&value>25);bar.classList.toggle('danger',value<=25)}
function startBattle(){if(mode!=='field')return;pos.dx=pos.dy=0;nub.style.transform='none';enemy=100;ally=100;setHp('#ehp',enemy);setHp('#ahp',ally);$('#ally-hp-text').textContent='28 / 28';busy=false;setPartnerArt();$('#main-actions').classList.remove('hidden');$('#move-actions').classList.add('hidden');show('battle');$('#message').textContent='野生のノイズラットが現れた！'}
function returnToField(){pos.x=52;pos.y=67;pos.px=47;pos.py=72;encounterCooldown=240;show('field');$('#objective').textContent='別の草むらを調査しよう'}
function gainExperience(amount){const oldLevel=currentLevel();experience+=amount;localStorage.setItem('codebeasts:exp',experience);const newLevel=currentLevel();setPartnerArt();return newLevel>oldLevel?` ${names[partner]}はLv.${newLevel}になった！`:` 経験値を${amount}獲得。`}
$('#fight').onclick=()=>{$('#main-actions').classList.add('hidden');$('#move-actions').classList.remove('hidden');$('#message').textContent='使う技を選ぼう。'};
$('#moves-back').onclick=()=>{$('#move-actions').classList.add('hidden');$('#main-actions').classList.remove('hidden');$('#message').textContent='どうする？'};
document.querySelectorAll('[data-hit]').forEach(button=>button.onclick=()=>{if(busy||mode!=='battle')return;const damage=Number(button.dataset.hit);if(!damage){$('#message').textContent='解析：ノイズラットは電脳型。残りHPは約'+enemy+'%。';return}busy=true;$('#move-actions').classList.add('hidden');$('.ally').classList.add('ally-attack');$('#message').textContent=`${names[partner]}の「${button.querySelector('b').textContent}」！`;setTimeout(()=>{$('.ally').classList.remove('ally-attack');$('.enemy').classList.add('enemy-hurt');$('#battle').classList.add('battle-hit');enemy=Math.max(0,enemy-damage);setHp('#ehp',enemy)},330);setTimeout(()=>{$('.enemy').classList.remove('enemy-hurt');$('#battle').classList.remove('battle-hit');if(enemy===0){$('#message').textContent='ノイズラットを倒した！'+gainExperience(18);setTimeout(returnToField,1250);return}$('#message').textContent='ノイズラットのグリッチバイト！';$('.ally').classList.add('ally-hurt');ally=Math.max(0,ally-18);setHp('#ahp',ally);$('#ally-hp-text').textContent=Math.ceil(28*ally/100)+' / 28';setTimeout(()=>{$('.ally').classList.remove('ally-hurt');busy=false;$('#main-actions').classList.remove('hidden');$('#message').textContent=ally?'次の行動を選ぼう。':'相棒のデータが停止した……'},430)},760)});
$('#capture').onclick=()=>{if(busy||mode!=='battle')return;busy=true;const chance=enemy<30?.8:enemy<60?.45:.15,success=Math.random()<chance;$('#battle').classList.add('battle-hit');if(success&&!party.includes('ノイズラット')){party.push('ノイズラット');localStorage.setItem('codebeasts:party',JSON.stringify(party))}$('#message').textContent=success?'LINK COMPLETE——ノイズラットがチームに加わった！'+gainExperience(10):'LINK ERROR——接続を弾かれた！';setTimeout(()=>{$('#battle').classList.remove('battle-hit');busy=false;if(success)returnToField()},1400)};
$('#bag').onclick=()=>{$('#message').textContent='バッグは次の更新で使えるようになります。'};
$('#party').onclick=()=>{$('#message').textContent=`チーム：${names[partner]}${party.length?'・'+party.join('・'):'（空き5枠）'}`};
$('#run').onclick=()=>{if(!busy)returnToField()};
