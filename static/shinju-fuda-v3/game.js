const $=s=>document.querySelector(s), wait=ms=>new Promise(r=>setTimeout(r,ms));
const state={enemy:100,player:100,turn:0,busy:false,summoned:false};
const message=(text)=>{$('#message').innerHTML=text};
let hasMuu=localStorage.getItem('shinju-fuda:muu')==='1';

function refreshBook(){
  $('#book-count').textContent=hasMuu?'2':'1';
  $('#muu-entry').classList.toggle('locked',!hasMuu);
  $('#switch-muu').disabled=!hasMuu;
  $('#river-node').classList.toggle('unlocked',hasMuu);
  $('#book-note').textContent=hasMuu?'新しい縁が、札帳に刻まれた。':'神獣との縁は、ここに刻まれる。';
}
refreshBook();
$('#book-button').addEventListener('click',()=>$('#book').classList.add('active'));
$('#book-close').addEventListener('click',()=>$('#book').classList.remove('active'));
$('#keep-card').addEventListener('click',()=>{
  hasMuu=true; localStorage.setItem('shinju-fuda:muu','1'); refreshBook();
  $('#reward').classList.remove('active'); $('#book').classList.add('active');
});
$('#river-node').addEventListener('click',()=>{
  const box=$('.notice');
  box.innerHTML=hasMuu?'<b>水元河川敷に新しい反応</b><span>水面の下で、青い神印が瞬いている……</span>':'<b>まだ道が開いていない</b><span>夕凪神社の禍獣と縁を結ぼう。</span>';
});

$('#sense').addEventListener('click',async()=>{
  $('#sense').disabled=true;
  $('#explore').classList.remove('active');
  await wait(420);
  $('#battle').classList.add('active');
});

$('#card').addEventListener('click',async()=>{
  if(state.summoned)return;
  state.summoned=true;
  message('札よ、結びを示せ——<br><b>来い、コハク！</b>');
  $('#card').classList.add('summoning');
  await wait(260);
  $('#kohaku').classList.add('show');
  await wait(650);
  $('#card').remove();
  $('#actions').classList.remove('hidden');
  $('#seal-action').classList.remove('hidden'); updateCaptureRate();
  $('#player-bar').classList.remove('hidden');
  message('相手は紫の気を溜めている。<br>次の一手を選べ。');
});

document.querySelectorAll('#actions button[data-move]').forEach(btn=>btn.addEventListener('click',()=>act(btn.dataset.move,+btn.dataset.damage)));
$('#seal-action').addEventListener('click',captureBeast);
$('#switch-action').addEventListener('click',()=>{$('#actions').classList.add('hidden');$('#seal-action').classList.add('hidden');$('#switch-panel').classList.remove('hidden')});
$('#switch-close').addEventListener('click',()=>{$('#switch-panel').classList.add('hidden');$('#actions').classList.remove('hidden');$('#seal-action').classList.remove('hidden')});
document.querySelectorAll('[data-beast]').forEach(btn=>btn.addEventListener('click',()=>switchBeast(btn.dataset.beast)));
function switchBeast(beast){
  const img=$('#kohaku'), moves=[...document.querySelectorAll('[data-move]')];
  if(beast==='muu'){
    img.src='assets/kagekui.png'; img.alt='夢獏ムウ';
    [['夢弾',20],['まどろみ',12],['見切る',0]].forEach((v,i)=>{moves[i].textContent=v[0];moves[i].dataset.move=v[0];moves[i].dataset.damage=v[1]});
    message('夢獏ムウと交代！<br>夢の力で戦場を包む。');
  }else{
    img.src='assets/kohaku.png'; img.alt='炎狐コハク';
    [['狐火',24],['印返し',15],['見切る',0]].forEach((v,i)=>{moves[i].textContent=v[0];moves[i].dataset.move=v[0];moves[i].dataset.damage=v[1]});
    message('炎狐コハクと交代！<br>炎の気が再び燃え上がる。');
  }
  $('#switch-panel').classList.add('hidden'); $('#actions').classList.remove('hidden'); $('#seal-action').classList.remove('hidden');
}
function captureChance(){return state.enemy<=15?85:state.enemy<=35?60:state.enemy<=60?30:15}
function updateCaptureRate(){$('#seal-action small').textContent=`捕獲率 ${captureChance()}%`}
function effect(name,duration=760){
  const layer=$('#battle-effect'); layer.className='battle-effect '+name;
  setTimeout(()=>layer.className='battle-effect',duration);
}
async function act(move,damage){
  if(state.busy)return;
  state.busy=true; $('#actions').classList.add('hidden'); $('#seal-action').classList.add('hidden'); state.turn++;
  if(move==='見切る'){
    effect('read',1000);
    message('コハクは気配を読む……<br>次の攻撃は「夢喰らい」だ！');
    await wait(850); state.player=Math.max(0,state.player-5);
  }else{
    const bonus=move==='印返し'&&state.turn%2===0?8:0;
    effect(move==='狐火'?'foxfire':'reflect',850);
    state.enemy=Math.max(0,state.enemy-damage-bonus);
    $('#enemy-hp').style.width=state.enemy+'%';
    message(`コハクの「${move}」！<br>結界を ${damage+bonus} 削った！`);
    $('#kohaku').classList.add('attack');
    await wait(130); $('#fx').classList.add('fire'); $('#enemy').classList.add('hurt'); $('#game').classList.add('game-shake');
    await wait(350); $('#kohaku').classList.remove('attack'); $('#fx').classList.remove('fire'); $('#enemy').classList.remove('hurt');
    $('#game').classList.remove('game-shake');
  }
  if(state.enemy<=0){await wait(420);beastDefeated();state.busy=false;return;}
  await wait(500); state.player=Math.max(0,state.player-(move==='見切る'?5:12));
  $('#player-hp').style.width=state.player+'%';
  $('#kohaku').classList.add('hurt');
  message('影喰いの獏の反撃！<br>コハクはまだ戦える。');
  await wait(380); $('#kohaku').classList.remove('hurt');
  await wait(270); message('敵の気配が揺らいだ。どう指示する？');
  updateCaptureRate(); $('#actions').classList.remove('hidden'); $('#seal-action').classList.remove('hidden'); state.busy=false;
}
function beastDefeated(){
  $('#seal-action').classList.add('hidden'); $('#enemy').classList.add('sealed');
  message('禍獣を倒した。<br><b>神獣札にはできなかった……</b>');
  $('#actions').innerHTML='<button id="retry">探索へ戻る</button>';
  $('#actions').style.gridTemplateColumns='1fr'; $('#actions').classList.remove('hidden');
  $('#retry').addEventListener('click',()=>location.reload());
}
async function captureBeast(){
  if(state.busy)return; state.busy=true;
  $('#seal-action').classList.add('hidden'); $('#actions').classList.add('hidden');
  message('白紙の神獣札——<br><b>その魂を結べ！</b>');
  const seal=$('#seal-throw'); seal.classList.add('throw');
  await wait(720);
  if(Math.random()*100>=captureChance()){
    message('札が弾かれた！<br>もう少し弱らせる必要がありそうだ。');
    $('#game').classList.add('game-shake'); await wait(420); $('#game').classList.remove('game-shake');
    seal.classList.remove('throw');
    state.player=Math.max(0,state.player-10); $('#player-hp').style.width=state.player+'%';
    await wait(650); $('#actions').classList.remove('hidden'); $('#seal-action').classList.remove('hidden'); state.busy=false; return;
  }
  $('#enemy').classList.add('sealed'); $('#game').classList.add('capture-flash');
  message('一度……　二度……<br>札の中で気配が揺れている！');
  await wait(900); message('三度——<br><b>神獣の魂が札と結ばれた！</b>');
  await wait(850); $('#battle').classList.remove('active'); $('#reward').classList.add('active');
}
