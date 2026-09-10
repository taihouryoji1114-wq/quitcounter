const ASSET='/static/digital-monsters/sprites/starters/';
const monsters={
  fire:{walk:'fire-walk-4x4-v5.png',thumb:'fire-starter-four-directions.png',columns:4},
  water:{walk:'water-walk-4x4-v4.png',thumb:'water-starter-four-directions.png',columns:4},
  nature:{walk:'nature-walk-3x4.png',thumb:'nature-starter-four-directions.png',columns:3},
  chankocchi:{walk:'chankocchi-walk-3x4.png',thumb:'chankocchi-four-directions.png',columns:3}
};
const directionRows={down:0,up:1,right:2,left:3};
const room=document.querySelector('#room');
const residents=[
  {kind:'fire',actor:document.querySelector('#actor-fire'),canvas:document.querySelector('#sprite-fire'),thought:document.querySelector('#thought-fire'),state:document.querySelector('#state-fire'),x:.31,y:.67,target:{x:.55,y:.55},direction:'right',frame:1,nextTarget:0,lastThought:0,image:null},
  {kind:'water',actor:document.querySelector('#actor-water'),canvas:document.querySelector('#sprite-water'),thought:document.querySelector('#thought-water'),state:document.querySelector('#state-water'),x:.68,y:.61,target:{x:.42,y:.73},direction:'left',frame:1,nextTarget:900,lastThought:0,image:null},
];
function renderResident(value){const choice=monsters[value.kind],image=value.image,canvas=value.canvas;if(!image||!image.complete||!image.naturalWidth)return;const context=canvas.getContext('2d'),cellWidth=image.naturalWidth/choice.columns,cellHeight=image.naturalHeight/4,mirror=value.direction==='right',row=mirror?directionRows.left:directionRows[value.direction];context.imageSmoothingEnabled=false;context.clearRect(0,0,canvas.width,canvas.height);context.save();if(mirror){context.translate(canvas.width,0);context.scale(-1,1)}context.drawImage(image,value.frame*cellWidth,row*cellHeight,cellWidth,cellHeight,0,0,canvas.width,canvas.height);context.restore()}
function parkBlocked(x,y){if(x<.08||x>.92||y<.31||y>.87)return true;const pond=((x-.80)/.17)**2+((y-.46)/.14)**2<1;const bench=x>.40&&x<.66&&y>.39&&y<.50;return pond||bench}
function chooseResidentTarget(value,nearFriend=false){let nx,ny,tries=0;do{if(nearFriend){const friend=residents.find(other=>other!==value);nx=friend.x+(Math.random()-.5)*.18;ny=friend.y+(Math.random()-.5)*.14}else{nx=.11+Math.random()*.78;ny=.34+Math.random()*.49}tries++}while(parkBlocked(nx,ny)&&tries<20);value.target={x:nx,y:ny};value.nextTarget=performance.now()+1700+Math.random()*3000}
function residentThought(value){if(value.thought.classList.contains('show'))return;value.thought.textContent=['♪','…','!','♡','?'][Math.floor(Math.random()*5)];value.thought.style.left=`calc(${value.x*100}% + 12px)`;value.thought.style.top=`calc(${value.y*100}% - 42px)`;value.thought.classList.add('show');setTimeout(()=>value.thought.classList.remove('show'),1800)}
residents.forEach(value=>{value.actor.classList.add('precise-cycle');value.image=new Image();value.image.decoding='async';value.image.onload=()=>renderResident(value);value.image.src=`${ASSET}${monsters[value.kind].walk}`});
let parkLast=performance.now();
function tick(now){const dt=Math.min(.035,(now-parkLast)/1000);parkLast=now;residents.forEach((value,index)=>{if(now>value.nextTarget)chooseResidentTarget(value,Math.random()<.28);const dx=value.target.x-value.x,dy=value.target.y-value.y,dist=Math.hypot(dx,dy),moving=dist>.008;if(moving){const speed=(.075+index*.006)*dt,nx=value.x+dx/dist*Math.min(dist,speed),ny=value.y+dy/dist*Math.min(dist,speed);if(!parkBlocked(nx,value.y))value.x=nx;if(!parkBlocked(value.x,ny))value.y=ny;const dir=Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up');if(dir!==value.direction)value.direction=dir;value.actor.classList.add('moving');const frame=[0,1,2,3][Math.floor((now+index*70)/145)%4];if(frame!==value.frame){value.frame=frame;renderResident(value)}value.state.textContent=index?'公園を散歩中':'公園を探検中'}else{value.actor.classList.remove('moving');if(value.frame!==1){value.frame=1;renderResident(value)}value.state.textContent=Math.hypot(value.x-residents[1-index].x,value.y-residents[1-index].y)<.2?'いっしょに過ごしている':'のんびり休憩中';if(now-value.lastThought>5000&&Math.random()<.006){value.lastThought=now;residentThought(value)}}value.actor.style.left=`${value.x*100}%`;value.actor.style.top=`${value.y*100}%`});requestAnimationFrame(tick)}
room.addEventListener('pointerdown',()=>residents.forEach(value=>chooseResidentTarget(value,Math.random()<.5)));
document.querySelectorAll('[data-lab]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.lab==='バトル'){startBattle();return}
  if(button.dataset.lab==='街'){openTown();return}
  residents.forEach(value=>residentThought(value));
}));

const battle=document.querySelector('#battle'),battleMessage=document.querySelector('#battle-message');
const battleCommand=document.querySelector('#battle-command'),battleMoves=document.querySelector('#battle-moves');
const playerHpBar=document.querySelector('#player-hp'),enemyHpBar=document.querySelector('#enemy-hp');
const playerHpText=document.querySelector('#player-hp-text'),playerHpMax=document.querySelector('#player-hp-max');
const playerLevel=document.querySelector('#player-level'),playerXpBar=document.querySelector('#player-xp');
const playerBattler=document.querySelector('#player-battler'),enemyBattler=document.querySelector('#enemy-battler');
const moveLearn=document.querySelector('#move-learn'),moveBack=document.querySelector('#move-back');
const TYPE_CHART={fire:{nature:2,water:.5},water:{fire:2,nature:.5},nature:{water:2,fire:.5}};
const MOVE_DATA={
  ember:{name:'ひのこ',type:'fire',power:[4,6]},tackle:{name:'たいあたり',type:'normal',power:[3,5]},
  tail:{name:'しっぽアタック',type:'normal',power:[4,5]},guard:{name:'ほのおのまもり',type:'fire',guard:true},
  fireFang:{name:'ほのおのキバ',type:'fire',power:[6,8]},flameWheel:{name:'かえんぐるま',type:'fire',power:[7,9]},
};
const TYPE_NAME={fire:'ほのお',water:'みず',nature:'みどり',normal:'ノーマル'};
const LEARN_LEVELS={6:'fireFang',8:'flameWheel'};
function loadProfile(){
  try{
    const saved=JSON.parse(localStorage.getItem('laboIgnisProfile')||'{}');
    return {level:Math.max(5,Number(saved.level)||5),xp:Math.max(0,Number(saved.xp)||0),stage:Math.max(1,Number(saved.stage)||1),moves:Array.isArray(saved.moves)&&saved.moves.length?saved.moves.slice(0,4):['ember','tackle','tail','guard'],pendingMove:saved.pendingMove||null};
  }catch(_){return {level:5,xp:0,stage:1,moves:['ember','tackle','tail','guard'],pendingMove:null}}
}
let profile=loadProfile(),battleState={player:24,playerMax:24,enemy:24,busy:false,guard:false,over:false};
function saveProfile(){localStorage.setItem('laboIgnisProfile',JSON.stringify(profile))}
function xpNeeded(){return profile.level*12}
function typeMultiplier(attackType,defenderType){return TYPE_CHART[attackType]?.[defenderType]||1}

function drawBattleSprite(canvas,file,column){
  const image=new Image();image.onload=()=>{
    const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
    context.clearRect(0,0,canvas.width,canvas.height);
    const width=image.naturalWidth/2,height=image.naturalHeight/2;
    context.drawImage(image,column*width,0,width,height,0,0,canvas.width,canvas.height);
  };image.src=`${ASSET}${file}`;
}
function updateBattleHp(){
  playerHpBar.style.width=`${Math.max(0,battleState.player)/battleState.playerMax*100}%`;
  enemyHpBar.style.width=`${Math.max(0,battleState.enemy)/24*100}%`;
  playerHpText.textContent=Math.max(0,battleState.player);
  playerHpMax.textContent=battleState.playerMax;playerLevel.textContent=`Lv.${profile.level}　火`;
  playerXpBar.style.width=`${Math.min(100,profile.xp/xpNeeded()*100)}%`;
  playerHpBar.classList.toggle('low',battleState.player<=battleState.playerMax*.3);enemyHpBar.classList.toggle('low',battleState.enemy<=7);
}
function renderMoves(){
  battleMoves.querySelectorAll('[data-move]').forEach(button=>button.remove());
  profile.moves.forEach(id=>{const move=MOVE_DATA[id];if(!move)return;const button=document.createElement('button');button.type='button';button.dataset.move=id;button.innerHTML=`<b>${move.name}</b><small>${TYPE_NAME[move.type]}</small>`;button.addEventListener('click',()=>useMove(id));battleMoves.insertBefore(button,moveBack)});
}
function showCommands(){battleCommand.hidden=false;battleMoves.hidden=true;moveLearn.hidden=true}
function showMoves(){if(battleState.busy||battleState.over)return;renderMoves();battleCommand.hidden=true;battleMoves.hidden=false;moveLearn.hidden=true;battleMessage.textContent='どの技を つかう？'}
function battleText(text,delay=720){battleMessage.textContent=text;return new Promise(resolve=>setTimeout(resolve,delay))}
function clearBattleEffect(target){target.getAnimations?.().forEach(animation=>animation.cancel());target.classList.remove('hit','attack');target.style.animation='none';target.style.filter='drop-shadow(0 4px 0 #0002)';void target.offsetWidth;target.style.removeProperty('animation')}
function animateOnce(target,name){clearBattleEffect(target);void target.offsetWidth;target.classList.add(name);setTimeout(()=>clearBattleEffect(target),460)}
function battleHit(target){animateOnce(target,'hit')}
function battleAttack(target){animateOnce(target,'attack')}
function damage(min,max){return min+Math.floor(Math.random()*(max-min+1))}

function showMoveReplacement(newMoveId){
  profile.pendingMove=newMoveId;saveProfile();battleCommand.hidden=true;battleMoves.hidden=true;moveLearn.hidden=false;moveLearn.replaceChildren();
  const title=document.createElement('p');title.textContent=`${MOVE_DATA[newMoveId].name}を覚える。忘れる技を選んでください。`;moveLearn.append(title);
  profile.moves.forEach((oldId,index)=>{const button=document.createElement('button');button.type='button';button.textContent=`${MOVE_DATA[oldId].name}と交換`;button.addEventListener('click',()=>{profile.moves[index]=newMoveId;profile.pendingMove=null;saveProfile();moveLearn.hidden=true;battleMessage.textContent=`${MOVE_DATA[newMoveId].name}を おぼえた！`});moveLearn.append(button)});
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='今は覚えない';cancel.addEventListener('click',()=>{profile.pendingMove=null;saveProfile();moveLearn.hidden=true;battleMessage.textContent='技を覚えずに終えた'});moveLearn.append(cancel);
}
async function awardExperience(){
  const gained=40;profile.xp+=gained;await battleText(`経験値を ${gained} かくとく！`);let learned=null,evolved=false;
  while(profile.xp>=xpNeeded()){
    profile.xp-=xpNeeded();profile.level+=1;await battleText(`イグニスは Lv.${profile.level}に あがった！`);
    if(LEARN_LEVELS[profile.level])learned=LEARN_LEVELS[profile.level];
    if(profile.level>=10&&profile.stage===1){profile.stage=2;evolved=true}
  }
  saveProfile();updateBattleHp();
  if(evolved)await battleText('イグニスに 進化の力が めばえた！');
  if(learned){if(profile.moves.length<4){profile.moves.push(learned);saveProfile();await battleText(`${MOVE_DATA[learned].name}を おぼえた！`)}else showMoveReplacement(learned)}
}

async function useMove(name){
  if(battleState.busy||battleState.over)return;battleState.busy=true;battleMoves.hidden=true;
  const move=MOVE_DATA[name];
  if(!move){battleState.busy=false;return}
  if(move.guard){
    battleState.guard=true;battleAttack(playerBattler);await battleText('イグニスは ほのおのまもりを まとった！');
  }else{
    const multiplier=typeMultiplier(move.type,'water');battleAttack(playerBattler);await battleText(`イグニスの ${move.name}！`,480);
    battleHit(enemyBattler);battleState.enemy-=Math.max(1,Math.round((damage(...move.power)+Math.floor((profile.level-5)/2))*multiplier));updateBattleHp();
    await battleText(multiplier>1?'効果は ばつぐんだ！':multiplier<1?'効果は いまひとつ…':'アクアロに ダメージ！');
  }
  if(battleState.enemy<=0){battleState.over=true;await battleText('アクアロは たおれた！');battle.classList.add('battle-won');await awardExperience();if(!profile.pendingMove)battleMessage.textContent='イグニスの かち！　画面をタップして再戦';battleState.busy=false;return}
  const enemyMove=Math.random()<.68?{name:'みずでっぽう',type:'water',power:[4,6]}:{name:'たいあたり',type:'normal',power:[3,5]};
  battleAttack(enemyBattler);await battleText(`アクアロの ${enemyMove.name}！`,480);
  const multiplier=typeMultiplier(enemyMove.type,'fire');battleHit(playerBattler);let hit=Math.max(1,Math.round(damage(...enemyMove.power)*multiplier));if(battleState.guard){hit=Math.max(1,Math.floor(hit/2));battleState.guard=false}
  battleState.player-=hit;updateBattleHp();await battleText(multiplier>1?'効果は ばつぐんだ！':multiplier<1?'効果は いまひとつ…':'イグニスに ダメージ！');
  if(battleState.player<=0){battleState.over=true;await battleText('イグニスは たおれた！');battleMessage.textContent='アクアロの かち！　画面をタップして再戦';battle.classList.add('battle-lost')}
  else{battleMessage.textContent='イグニスは どうする？';showCommands()}
  battleState.busy=false;
}
function startBattle(){
  const maxHp=24+(profile.level-5)*4;battleState={player:maxHp,playerMax:maxHp,enemy:24,busy:false,guard:false,over:false};
  battle.classList.remove('battle-won','battle-lost');clearBattleEffect(playerBattler);clearBattleEffect(enemyBattler);battle.hidden=false;updateBattleHp();showCommands();
  battleMessage.textContent='アクアロが あらわれた！';
  drawBattleSprite(playerBattler,monsters.fire.thumb,1);drawBattleSprite(enemyBattler,monsters.water.thumb,0);
  setTimeout(()=>{if(!battleState.busy&&!battleState.over)battleMessage.textContent='イグニスは どうする？'},800);
}
function closeBattle(){battle.hidden=true}
document.querySelector('#battle-close').addEventListener('click',closeBattle);
document.querySelector('#move-back').addEventListener('click',()=>{battleMessage.textContent='イグニスは どうする？';showCommands()});
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.command==='fight'){showMoves();return}
  if(button.dataset.command==='run'){closeBattle();return}
  battleMessage.textContent=button.dataset.command==='party'?'交代できる仲間は まだいない！':'どうぐは まだ持っていない！';
}));
battleMessage.addEventListener('click',()=>{if(battleState.over&&!profile.pendingMove)startBattle()});
[playerBattler,enemyBattler].forEach(target=>target.addEventListener('animationend',()=>clearBattleEffect(target)));

const town=document.querySelector('#town'),townMap=document.querySelector('#town-map'),townHero=document.querySelector('#town-hero'),townCanvas=document.querySelector('#town-canvas');
const TOWN_W=640,TOWN_H=576,TILE=32;
let townPosition={x:320,y:490},townDirection=null,townLast=performance.now();
const townBlockedTiles=new Set();
function blockTownRect(x,y,w,h){for(let row=y;row<y+h;row++)for(let col=x;col<x+w;col++)townBlockedTiles.add(`${col},${row}`)}
function prepareTownCollision(){townBlockedTiles.clear();for(let x=0;x<20;x++){townBlockedTiles.add(`${x},0`);townBlockedTiles.add(`${x},17`)}for(let y=0;y<18;y++){townBlockedTiles.add(`0,${y}`);townBlockedTiles.add(`19,${y}`)}blockTownRect(2,2,5,5);blockTownRect(13,2,5,5);blockTownRect(13,12,5,5);blockTownRect(2,12,5,5);blockTownRect(1,7,3,1);blockTownRect(16,8,3,1)}
function townBlocked(x,y){const points=[[x-9,y-5],[x+9,y-5],[x-9,y+5],[x+9,y+5]];return points.some(([px,py])=>townBlockedTiles.has(`${Math.floor(px/TILE)},${Math.floor(py/TILE)}`))}
function drawTownMap(){const c=townCanvas.getContext('2d');c.imageSmoothingEnabled=false;const rect=(x,y,w,h,color)=>{c.fillStyle=color;c.fillRect(x*TILE,y*TILE,w*TILE,h*TILE)};for(let y=0;y<18;y++)for(let x=0;x<20;x++){rect(x,y,1,1,(x+y)%2?'#79bd62':'#74b75e');c.fillStyle='#65a850';c.fillRect(x*TILE+5,y*TILE+7,3,5);c.fillRect(x*TILE+23,y*TILE+20,2,4)}rect(8,0,4,18,'#e7ce98');rect(0,8,20,3,'#e7ce98');for(let y=0;y<18;y++){c.fillStyle='#cfb77e';c.fillRect(8*TILE,y*TILE,4,3)}for(let x=0;x<20;x++){c.fillStyle='#cfb77e';c.fillRect(x*TILE,8*TILE,3,3)}
  const tree=(x,y)=>{rect(x,y,1,1,'#3f783f');c.fillStyle='#28613a';c.fillRect(x*TILE+3,y*TILE+2,26,23);c.fillStyle='#4d914b';c.fillRect(x*TILE+7,y*TILE+3,18,13);c.fillStyle='#795132';c.fillRect(x*TILE+13,y*TILE+23,6,9)};for(let x=0;x<20;x++){tree(x,0);tree(x,17)}for(let y=1;y<17;y++){tree(0,y);tree(19,y)}
  const house=(x,y,wall,roof,label)=>{rect(x,y+2,5,3,wall);c.fillStyle=roof;c.fillRect(x*TILE-5,y*TILE+18,5*TILE+10,38);c.fillStyle='#703f37';for(let i=0;i<5;i++)c.fillRect(x*TILE-3+i*34,y*TILE+22,30,5);c.fillStyle='#f3e8b7';c.fillRect((x+1)*TILE,(y+3)*TILE,24,20);c.fillRect((x+3)*TILE,(y+3)*TILE,24,20);c.fillStyle='#76503a';c.fillRect((x+2)*TILE+5,(y+3)*TILE,22,64);c.fillStyle='#fff8d9';c.fillRect(x*TILE+18,(y+5)*TILE-7,124,18);c.fillStyle='#294a3d';c.font='bold 12px sans-serif';c.textAlign='center';c.fillText(label,x*TILE+80,(y+5)*TILE+7)};house(2,2,'#f1dfb4','#bd5947','主人公の家');house(13,2,'#d7edf0','#4b8190','モンスター研究所');house(13,12,'#f4d7a1','#d8893d','道具屋');
  rect(2,12,5,5,'#d1c779');c.fillStyle='#51aabc';c.fillRect(2*TILE+8,12*TILE+8,5*TILE-16,5*TILE-16);c.strokeStyle='#9ee4e5';c.lineWidth=4;for(let i=0;i<4;i++){c.beginPath();c.arc(2*TILE+80,12*TILE+80,18+i*17,0,Math.PI*2);c.stroke()}
  c.fillStyle='#a87544';c.fillRect(3*TILE,7*TILE+5,72,22);c.fillStyle='#fff5ce';c.font='bold 10px sans-serif';c.fillText('ミナモ町',3*TILE+36,7*TILE+20);c.fillStyle='#fff';c.font='bold 10px sans-serif';c.fillText('↑ 1ばん道路',10*TILE,28);c.fillStyle='#e95b65';for(const [x,y] of [[7,3],[7,4],[12,13],[7,14]]){c.fillRect(x*TILE+7,y*TILE+9,5,5);c.fillRect(x*TILE+18,y*TILE+18,5,5)}
}
function paintTownHero(){townHero.style.left=`${townPosition.x/TOWN_W*100}%`;townHero.style.top=`${townPosition.y/TOWN_H*100}%`;townHero.classList.toggle('walking',!!townDirection);townHero.classList.remove('face-up','face-down','face-left','face-right');townHero.classList.add(`face-${townDirection||'down'}`)}
function openTown(){town.hidden=false;drawTownMap();paintTownHero()}
function closeTown(){townDirection=null;town.hidden=true;paintTownHero()}
function moveTown(now){const dt=Math.min(.04,(now-townLast)/1000);townLast=now;if(!town.hidden&&townDirection){const speed=155*dt;let nx=townPosition.x+(townDirection==='left'?-speed:townDirection==='right'?speed:0),ny=townPosition.y+(townDirection==='up'?-speed:townDirection==='down'?speed:0);if(!townBlocked(nx,townPosition.y))townPosition.x=nx;if(!townBlocked(townPosition.x,ny))townPosition.y=ny;paintTownHero()}requestAnimationFrame(moveTown)}
document.querySelector('#town-close').addEventListener('click',closeTown);
document.querySelectorAll('[data-town-dir]').forEach(button=>{const begin=event=>{event.preventDefault();townDirection=button.dataset.townDir;paintTownHero()};const end=()=>{townDirection=null;paintTownHero()};button.addEventListener('pointerdown',begin);button.addEventListener('pointerup',end);button.addEventListener('pointercancel',end);button.addEventListener('pointerleave',end)});
document.addEventListener('keydown',event=>{if(town.hidden)return;const key={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right'}[event.key];if(key){event.preventDefault();townDirection=key;paintTownHero()}});
document.addEventListener('keyup',event=>{if(!town.hidden&&event.key.startsWith('Arrow')){townDirection=null;paintTownHero()}});
requestAnimationFrame(moveTown);
prepareTownCollision();drawTownMap();
document.addEventListener('contextmenu',event=>{if(event.target.closest('.app,.battle-screen,.town-screen'))event.preventDefault()});
document.addEventListener('selectstart',event=>{if(event.target.closest('.app,.battle-screen,.town-screen'))event.preventDefault()});
residents.forEach(value=>chooseResidentTarget(value));requestAnimationFrame(tick);
