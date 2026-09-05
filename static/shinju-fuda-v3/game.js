const $=s=>document.querySelector(s), wait=ms=>new Promise(r=>setTimeout(r,ms));
const state={enemy:100,player:100,turn:0,busy:false,summoned:false};
const message=(text)=>{$('#message').innerHTML=text};

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
async function act(move,damage){
  if(state.busy||state.enemy<=0)return;
  state.busy=true; $('#actions').classList.add('hidden'); state.turn++;
  if(move==='見切る'){
    message('コハクは気配を読む……<br>次の攻撃は「夢喰らい」だ！');
    await wait(850); state.player=Math.max(0,state.player-5);
  }else{
    const bonus=move==='印返し'&&state.turn%2===0?8:0;
    state.enemy=Math.max(0,state.enemy-damage-bonus);
    $('#enemy-hp').style.width=state.enemy+'%';
    message(`コハクの「${move}」！<br>結界を ${damage+bonus} 削った！`);
    $('#kohaku').classList.add('attack');
    await wait(130); $('#fx').classList.add('fire'); $('#enemy').classList.add('hurt');
    await wait(350); $('#kohaku').classList.remove('attack'); $('#fx').classList.remove('fire'); $('#enemy').classList.remove('hurt');
  }
  if(state.enemy<=0){await wait(500); showContract();state.busy=false;return;}
  await wait(500); state.player=Math.max(0,state.player-(move==='見切る'?5:12));
  $('#player-hp').style.width=state.player+'%';
  $('#kohaku').classList.add('hurt');
  message('影喰いの獏の反撃！<br>コハクはまだ戦える。');
  await wait(380); $('#kohaku').classList.remove('hurt');
  await wait(270); message('敵の気配が揺らいだ。どう指示する？');
  $('#actions').classList.remove('hidden'); state.busy=false;
}
function showContract(){
  message('契りの刻！<br>白紙の札へ迎えよう。');
  $('#actions').innerHTML='<button id="contract">神獣契約を結ぶ</button>';
  $('#actions').style.gridTemplateColumns='1fr'; $('#actions').classList.remove('hidden');
  $('#contract').addEventListener('click',()=>{
    $('#enemy').style.transition='.55s'; $('#enemy').style.opacity='0'; $('#enemy').style.transform='scale(.08)';
    $('#actions').classList.add('hidden'); message('新たな神獣札「夢獏 ムウ」を手に入れた！<br><b>—— 試作版クリア ——</b>');
  });
}
