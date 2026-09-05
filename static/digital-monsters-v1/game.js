const $=s=>document.querySelector(s),screens=[...document.querySelectorAll('.screen')];
const names=['イグニス','アクアロ','リーフィ'],positions=['left','center','right'];
let partner=Number(localStorage.getItem('codebeasts:partner')||0),enemy=100,busy=false,mode='start',encounterCooldown=0;
function show(id){mode=id;screens.forEach(s=>s.classList.toggle('active',s.id===id))}
$('#begin').onclick=()=>show('choose');
document.querySelectorAll('[data-pick]').forEach(button=>button.onclick=()=>{
  const picked=Number(button.dataset.pick);
  if(button.classList.contains('selected')){partner=picked;localStorage.setItem('codebeasts:partner',partner);setPartnerArt();show('field');return}
  document.querySelectorAll('[data-pick]').forEach(item=>item.classList.remove('selected'));button.classList.add('selected');
  $('#choose-note').innerHTML=`<b>${names[picked]}</b>を選択中。もう一度タップして決定。`;
});
function setPartnerArt(){$('#partner i').style.backgroundPosition=positions[partner];$('#ally-art').style.backgroundPosition=positions[partner];$('#ally-name').textContent=names[partner]+'　Lv.5'}setPartnerArt();
const pos={x:32,y:62,px:27,py:67,dx:0,dy:0},stick=$('#stick'),nub=$('#stick i');let pid=null;
const obstacles=[[0,0,29,43],[0,68,27,100],[0,43,12,68],[35,0,55,31],[91,0,100,100],[29,0,35,27],[48,27,58,47],[69,0,91,13],[75,82,91,100],[34,86,75,100]];
function blocked(x,y){return obstacles.some(([l,t,r,b])=>x>l&&x<r&&y>t&&y<b)}
function move(event){if(event.pointerId!==pid||mode!=='field')return;const rect=stick.getBoundingClientRect(),x=event.clientX-rect.left-rect.width/2,y=event.clientY-rect.top-rect.height/2,d=Math.hypot(x,y),m=Math.min(35,d),nx=d?x/d:0,ny=d?y/d:0;pos.dx=nx*m/35;pos.dy=ny*m/35;nub.style.transform=`translate(${nx*m}px,${ny*m}px)`}
stick.onpointerdown=event=>{if(mode!=='field')return;pid=event.pointerId;stick.setPointerCapture(pid);move(event)};stick.onpointermove=move;
stick.onpointerup=stick.onpointercancel=event=>{if(event.pointerId!==pid)return;pid=null;pos.dx=pos.dy=0;nub.style.transform='none'};
function loop(){if(mode==='field'){if(encounterCooldown>0)encounterCooldown--;const nx=Math.max(3,Math.min(94,pos.x+pos.dx*.18)),ny=Math.max(9,Math.min(90,pos.y+pos.dy*.25));if(!blocked(nx,pos.y))pos.x=nx;if(!blocked(pos.x,ny))pos.y=ny;pos.px+=(pos.x-5-pos.px)*.045;pos.py+=(pos.y+4-pos.py)*.045;$('#hero').style.left=pos.x+'%';$('#hero').style.top=pos.y+'%';$('#partner').style.left=pos.px+'%';$('#partner').style.top=pos.py+'%';const inGrass=pos.x>58&&pos.x<89&&pos.y>14&&pos.y<80,moving=Math.hypot(pos.dx,pos.dy)>.1;if(inGrass&&moving&&encounterCooldown===0&&Math.random()<.012)startBattle()}requestAnimationFrame(loop)}requestAnimationFrame(loop);
function startBattle(){if(mode!=='field')return;pos.dx=pos.dy=0;nub.style.transform='none';enemy=100;$('#ehp').style.width='100%';busy=false;setPartnerArt();show('battle');$('#message').textContent='野生のノイズラットが現れた！'}
function returnToField(){pos.x=52;pos.y=67;pos.px=47;pos.py=72;encounterCooldown=240;show('field');$('#objective').textContent='別の草むらを調査しよう'}
document.querySelector('[data-hit]').onclick=()=>{if(busy||mode!=='battle')return;busy=true;enemy=Math.max(0,enemy-22);$('#ehp').style.width=enemy+'%';$('#message').textContent=`${names[partner]}のデータパルス！`;setTimeout(()=>{busy=false;if(enemy===0){$('#message').textContent='ノイズラットを倒した！ 研究区へ戻ります。';setTimeout(returnToField,900)}else $('#message').textContent='ノイズラットのHPを削った。どうする？'},650)};
$('#capture').onclick=()=>{if(busy||mode!=='battle')return;busy=true;const chance=enemy<30?.8:enemy<60?.45:.15,success=Math.random()<chance;$('#message').textContent=success?'リンク成功！ ノイズラットが仲間になった！':'リンクを弾かれた！ もう少しHPを減らそう。';setTimeout(()=>{busy=false;if(success)returnToField()},1000)};
$('#run').onclick=()=>{if(!busy)returnToField()};
