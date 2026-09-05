const $=s=>document.querySelector(s), wait=ms=>new Promise(r=>setTimeout(r,ms));
const state={enemy:100,player:100,turn:0,busy:false,summoned:false};
const message=(text)=>{$('#message').innerHTML=text};
let hasMuu=localStorage.getItem('shinju-fuda:muu')==='1';

function refreshBook(){
  $('#book-count').textContent=hasMuu?'2':'1';
  $('#muu-entry').classList.toggle('locked',!hasMuu);
  $('#book-note').textContent=hasMuu?'新しい縁が、札帳に刻まれた。':'神獣との縁は、ここに刻まれる。';
}
refreshBook();
$('#book-button').addEventListener('click',()=>$('#book').classList.add('active'));
$('#book-close').addEventListener('click',()=>$('#book').classList.remove('active'));
$('#keep-card').addEventListener('click',()=>{
  hasMuu=true; localStorage.setItem('shinju-fuda:muu','1'); refreshBook();
  $('#reward').classList.remove('active'); $('#book').classList.add('active');
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
  $('#player-bar').classList.remove('hidden');
  message('相手は紫の気を溜めている。<br>次の一手を選べ。');
});

document.querySelectorAll('#actions button').forEach(btn=>btn.addEventListener('click',()=>act(btn.dataset.move,+btn.dataset.damage)));
$('#seal-action').addEventListener('click',captureBeast);
function effect(name,duration=760){
  const layer=$('#battle-effect'); layer.className='battle-effect '+name;
  setTimeout(()=>layer.className='battle-effect',duration);
}
async function act(move,damage){
  if(state.busy)return;
  state.busy=true; $('#actions').classList.add('hidden'); state.turn++;
  if(move==='見切る'){
    effect('read',1000);
    message('コハクは気配を読む……<br>次の攻撃は「夢喰らい」だ！');
    await wait(850); state.player=Math.max(0,state.player-5);
  }else{
    const bonus=move==='印返し'&&state.turn%2===0?8:0;
    effect(move==='狐火'?'foxfire':'reflect',850);
    state.enemy=Math.max(1,state.enemy-damage-bonus);
    $('#enemy-hp').style.width=state.enemy+'%';
    message(`コハクの「${move}」！<br>結界を ${damage+bonus} 削った！`);
    $('#kohaku').classList.add('attack');
    await wait(130); $('#fx').classList.add('fire'); $('#enemy').classList.add('hurt'); $('#game').classList.add('game-shake');
    await wait(350); $('#kohaku').classList.remove('attack'); $('#fx').classList.remove('fire'); $('#enemy').classList.remove('hurt');
    $('#game').classList.remove('game-shake');
  }
  if(state.enemy<=35){await wait(420);readyToSeal();state.busy=false;return;}
  await wait(500); state.player=Math.max(0,state.player-(move==='見切る'?5:12));
  $('#player-hp').style.width=state.player+'%';
  $('#kohaku').classList.add('hurt');
  message('影喰いの獏の反撃！<br>コハクはまだ戦える。');
  await wait(380); $('#kohaku').classList.remove('hurt');
  await wait(270); message('敵の気配が揺らいだ。どう指示する？');
  $('#actions').classList.remove('hidden'); state.busy=false;
}
function readyToSeal(){
  $('#actions').classList.add('hidden'); $('#seal-action').classList.remove('hidden');
  message('禍獣が弱った！ 倒す前に、<br><b>白紙の神獣札で封じよう。</b>');
}
async function captureBeast(){
  if(state.busy)return; state.busy=true;
  $('#seal-action').classList.add('hidden');
  message('白紙の神獣札——<br><b>その魂を結べ！</b>');
  const seal=$('#seal-throw'); seal.classList.add('throw');
  await wait(720); $('#enemy').classList.add('sealed'); $('#game').classList.add('capture-flash');
  message('一度……　二度……<br>札の中で気配が揺れている！');
  await wait(900); message('三度——<br><b>神獣の魂が札と結ばれた！</b>');
  await wait(850); $('#battle').classList.remove('active'); $('#reward').classList.add('active');
}
