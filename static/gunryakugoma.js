(() => {
  const COLS = 10, ROWS = 7;
  const TYPES = {
    general: { name: '総大将', mark: '将', move: 1, range: 1 },
    infantry: { name: '歩兵', mark: '槍', move: 1, range: 1 },
    cavalry: { name: '騎兵', mark: '騎', move: 2, range: 1 },
    archer: { name: '弓兵', mark: '弓', move: 1, range: 2 },
  };
  const TYPE_COST = { infantry: 1, cavalry: 1.5, archer: 1.2 };
  const SIZE_COST = { 100: 120, 500: 450, 1000: 800, 5000: 3400, 10000: 6000 };
  const BUILDINGS = {
    fence: { name: '防柵', cost: 450, hp: 1200 },
    base: { name: '砦', cost: 1600, hp: 2400 },
    castle: { name: '城', cost: 3800, hp: 5000 },
  };
  let state;
  const $ = id => document.getElementById(id);
  const pos = (r, c) => r * COLS + c;
  const rc = p => [Math.floor(p / COLS), p % COLS];
  const dist = (a, b) => { const [ar, ac] = rc(a), [br, bc] = rc(b); return Math.abs(ar-br)+Math.abs(ac-bc); };
  const fmt = n => Math.max(0, Math.round(n)).toLocaleString('ja-JP');
  const unitsAt = (p, owner=null) => state.units.filter(u => u.pos === p && (!owner || u.owner === owner));
  const unitAt = (p, owner=null) => unitsAt(p, owner)[0];
  const defenderAt = (p, owner) => unitsAt(p, owner).sort((a,b) => (a.type === 'general') - (b.type === 'general'))[0];
  const buildingAt = p => state.buildings.find(b => b.pos === p);
  const terrainAt = p => state.terrain[p] || 'plain';

  function freshState() {
    return {
      turn: 1, phase: 'player', money: 4000, food: 7000,
      enemyMoney: 4000, enemyFood: 7000, selected: null, placement: null,
      terrain: { 14:'forest',15:'forest',24:'forest',35:'hill',36:'hill',43:'forest',54:'hill',55:'hill' },
      buildings: [
        { id:'phq', owner:'player', type:'castle', pos:60, hp:6000, maxHp:6000, hq:true },
        { id:'ehq', owner:'enemy', type:'castle', pos:9, hp:6000, maxHp:6000, hq:true },
        { id:'pfence', owner:'player', type:'fence', pos:41, hp:1200, maxHp:1200 },
        { id:'efence', owner:'enemy', type:'fence', pos:28, hp:1200, maxHp:1200 },
      ],
      units: [
        { id:'pg', owner:'player', type:'general', size:1500, pos:61, moved:false },
        { id:'pi', owner:'player', type:'infantry', size:1000, pos:50, moved:false },
        { id:'pa', owner:'player', type:'archer', size:500, pos:52, moved:false },
        { id:'pc', owner:'player', type:'cavalry', size:500, pos:62, moved:false },
        { id:'eg', owner:'enemy', type:'general', size:1500, pos:8, moved:false },
        { id:'ei', owner:'enemy', type:'infantry', size:1000, pos:19, moved:false },
        { id:'ea', owner:'enemy', type:'archer', size:500, pos:7, moved:false },
        { id:'ec', owner:'enemy', type:'cavalry', size:500, pos:17, moved:false },
      ],
      revealedToPlayer: [], revealedToEnemy: [],
      log: '城から軍資金と兵糧が届いた。', over:false,
    };
  }

  function foodCost(unit) { return Math.max(10, Math.ceil(unit.size / 100) * 4); }
  function income(owner) {
    const owned = state.buildings.filter(b => b.owner === owner);
    return owned.reduce((sum,b) => sum + (b.type === 'castle' ? 1000 : b.type === 'base' ? 350 : 0), 0);
  }
  function foodIncome(owner) {
    return state.buildings.filter(b => b.owner === owner).reduce((sum,b) => sum + (b.type === 'castle' ? 1600 : b.type === 'base' ? 500 : 0), 0);
  }
  function isVisibleTo(viewer, unit) {
    if (unit.owner === viewer || terrainAt(unit.pos) !== 'forest') return true;
    const list = viewer === 'player' ? state.revealedToPlayer : state.revealedToEnemy;
    return list.includes(unit.id);
  }
  function revealToOpponent(unit) {
    const key = unit.owner === 'player' ? 'revealedToEnemy' : 'revealedToPlayer';
    if (!state[key].includes(unit.id)) state[key].push(unit.id);
  }
  function hideAfterMove(unit) {
    state.revealedToPlayer = state.revealedToPlayer.filter(id=>id!==unit.id);
    state.revealedToEnemy = state.revealedToEnemy.filter(id=>id!==unit.id);
  }
  function mergeSameType(unit) {
    const mate = state.units.find(other=>other!==unit&&other.pos===unit.pos&&other.owner===unit.owner&&other.type===unit.type);
    if (!mate) return unit;
    mate.size += unit.size; mate.moved = mate.moved || unit.moved;
    state.units = state.units.filter(other=>other!==unit);
    return mate;
  }
  function log(message) { state.log = message; $('sk-log').textContent = message; }
  function showModal(title, text, mark='軍', button='閉じる', callback=null) {
    $('sk-modal-title').textContent = title; $('sk-modal-text').textContent = text; $('sk-modal-mark').textContent = mark;
    $('sk-modal-secondary').classList.add('is-hidden');
    $('sk-modal-primary').textContent = button; $('sk-modal').classList.remove('is-hidden');
    $('sk-modal-primary').onclick = () => { $('sk-modal').classList.add('is-hidden'); if (callback) callback(); };
  }

  function render() {
    $('sk-turn').textContent = state.turn; $('sk-phase').textContent = state.phase === 'player' ? 'あなたの軍議' : '敵軍進行中';
    $('sk-money').textContent = fmt(state.money); $('sk-food').textContent = fmt(state.food); $('sk-income').textContent = `+${fmt(income('player'))}`;
    const board = $('sk-board'); board.innerHTML = '';
    const targets = getTargets();
    for (let p=0; p<COLS*ROWS; p++) {
      const cell = document.createElement('button'); cell.type='button'; cell.className=`sk-cell terrain-${terrainAt(p)}`;
      if (targets.move.has(p) || targets.place.has(p)) cell.classList.add('target');
      if (targets.attack.has(p)) cell.classList.add('attack-target');
      if (state.selected && state.selected.pos === p) cell.classList.add('selected');
      const b = buildingAt(p), stack = unitsAt(p).filter(u=>isVisibleTo('player',u));
      if (b) cell.insertAdjacentHTML('beforeend', `<span class="sk-building ${b.type} ${b.owner}" title="${BUILDINGS[b.type].name}"></span>`);
      if (stack.length) cell.insertAdjacentHTML('beforeend', `<span class="sk-unit-stack count-${Math.min(stack.length,4)}">${stack.map((u,i)=>`<span class="sk-piece slot-${i+1} ${u.owner} ${u.moved?'moved':''}"><span class="crest">${TYPES[u.type].mark}</span><span class="troops">${fmt(u.size)}</span></span>`).join('')}</span>`);
      cell.onclick = () => onCell(p); board.appendChild(cell);
    }
    renderSelection();
  }

  function renderSelection() {
    const box = $('sk-selection');
    if (state.placement) {
      const label = state.placement.kind === 'unit' ? `${TYPES[state.placement.type].name} ${fmt(state.placement.size)}人` : BUILDINGS[state.placement.type].name;
      box.innerHTML = `<span class="sk-selection-icon">配</span><div><small>配置先を選択</small><strong>${label}</strong><p>金色に光るマスへ配置できます</p></div>`; return;
    }
    const u = state.selected;
    if (!u) { box.innerHTML='<span class="sk-selection-icon">軍</span><div><small>軍略</small><strong>動かす駒を選択</strong><p>自軍の駒をタップしてください</p></div>'; return; }
    const t=TYPES[u.type];
    box.innerHTML=`<span class="sk-selection-icon">${t.mark}</span><div><small>${t.name}</small><strong>${fmt(u.size)}人　兵糧 ${fmt(foodCost(u))}</strong><p>${u.moved?'このターンは行動済み':'金色＝移動　赤色＝攻撃'}</p></div>`;
  }

  function reachable(unit) {
    if (unit.moved) return new Set();
    const seen = new Set([unit.pos]), frontier=[{p:unit.pos,d:0}], out=new Set();
    while(frontier.length) {
      const {p,d}=frontier.shift(); if(d>=TYPES[unit.type].move) continue;
      for(const n of neighbors(p)) {
        if(seen.has(n)) continue; seen.add(n);
        const occupants=unitsAt(n), b=buildingAt(n);
        const visibleEnemy=occupants.some(x=>x.owner!==unit.owner&&isVisibleTo(unit.owner,x));
        if(visibleEnemy || (b && b.owner!==unit.owner) || (b && b.type==='fence')) continue;
        out.add(n); if(!occupants.length) frontier.push({p:n,d:d+1});
      }
    }
    return out;
  }
  function getTargets() {
    const result={move:new Set(),attack:new Set(),place:new Set()};
    if(state.placement) { validPlacementCells().forEach(p=>result.place.add(p)); return result; }
    const u=state.selected; if(!u || u.owner!=='player' || u.moved) return result;
    reachable(u).forEach(p=>result.move.add(p));
    for(let p=0;p<COLS*ROWS;p++) {
      const enemyU=unitsAt(p,'enemy').find(u=>isVisibleTo('player',u)), enemyB=buildingAt(p);
      if(dist(u.pos,p)<=TYPES[u.type].range && ((enemyU&&enemyU.owner==='enemy')||(enemyB&&enemyB.owner==='enemy'))) result.attack.add(p);
    }
    return result;
  }
  function neighbors(p) { const [r,c]=rc(p), a=[]; if(r>0)a.push(pos(r-1,c)); if(r<ROWS-1)a.push(pos(r+1,c)); if(c>0)a.push(pos(r,c-1)); if(c<COLS-1)a.push(pos(r,c+1)); return a; }
  function validPlacementCells(owner='player', kind=state.placement?.kind) {
    const anchors = kind === 'unit'
      ? state.buildings.filter(b => b.owner === owner && (b.type === 'castle' || b.type === 'base'))
      : [...state.units.filter(u=>u.owner===owner),...state.buildings.filter(b=>b.owner===owner)];
    const cells=new Set(); anchors.forEach(a=>neighbors(a.pos).forEach(p=>{
      const occupants=unitsAt(p), building=buildingAt(p);
      if(kind==='unit') {
        const type=state.placement?.type;
        if((!building || building.owner===owner) && !occupants.some(u=>u.owner!==owner)) cells.add(p);
      } else if(!occupants.length&&!building) cells.add(p);
    })); return cells;
  }

  function onCell(p) {
    if(state.over || state.phase!=='player') return;
    if(state.placement) { if(validPlacementCells().has(p)) completePlacement(p); else log('金色の配置可能マスを選んでください。'); return; }
    const friendly=unitsAt(p,'player');
    const u=state.selected;
    if(!u) {
      if(friendly.length===1){state.selected=friendly[0];closePanel();render();}
      else if(friendly.length>1) showStackPicker(friendly);
      else log('まず動かす自軍の駒を選んでください。');
      return;
    }
    const targets=getTargets();
    if(targets.move.has(p)) moveUnit(u,p);
    else if(targets.attack.has(p)) showBattlePreview(u,p);
    else {
      if(friendly.length===1){state.selected=friendly[0];closePanel();render();}
      else if(friendly.length>1) showStackPicker(friendly);
      else log('そのマスには行動できません。');
    }
  }
  function spendFood(owner, amount) {
    const key=owner==='player'?'food':'enemyFood'; if(state[key]<amount) return false; state[key]-=amount; return true;
  }
  function moveUnit(u,p) {
    const hiddenEnemies=unitsAt(p).filter(enemy=>enemy.owner!==u.owner&&!isVisibleTo(u.owner,enemy));
    if(hiddenEnemies.length){hiddenEnemies.forEach(revealToOpponent);log('伏兵だ！ 森から敵軍が姿を現した。');attack(u,p);return;}
    const cost=foodCost(u); if(!spendFood(u.owner,cost)){ log('兵糧が足りず、軍を動かせない。'); return; }
    hideAfterMove(u); u.pos=p; u.moved=true; const combined=mergeSameType(u); state.selected=null;
    const merged=combined!==u?' 同兵種と合流した。':'';
    log(`${TYPES[combined.type].name} ${fmt(combined.size)}人が進軍。兵糧を${fmt(cost)}消費。${merged}`); render();
  }
  function matchup(att,def) {
    if(att==='infantry'&&def==='archer')return 1.35; if(att==='archer'&&def==='cavalry')return 1.35; if(att==='cavalry'&&def==='infantry')return 1.35;
    if(def==='infantry'&&att==='archer')return .75; if(def==='archer'&&att==='cavalry')return .75; if(def==='cavalry'&&att==='infantry')return .75; return 1;
  }
  function nearbyGeneralBonus(unit) {
    return state.units.some(other=>other.owner===unit.owner&&other.type==='general'&&dist(other.pos,unit.pos)<=1) ? 1.12 : 1;
  }
  function defensiveFactor(p, owner) {
    let factor=terrainAt(p)==='forest'?.82:terrainAt(p)==='hill'?.88:1;
    const building=buildingAt(p);
    if(building&&building.owner===owner) factor*=building.type==='castle'?.66:building.type==='base'?.78:1;
    return factor;
  }
  function expectedDamage(attacker, defender, targetPos) {
    let factor=matchup(attacker.type,defender.type)*nearbyGeneralBonus(attacker)*defensiveFactor(targetPos,defender.owner);
    if(attacker.type==='cavalry'&&terrainAt(attacker.pos)==='forest') factor*=.78;
    return Math.max(20,Math.round(attacker.size*.46*factor));
  }
  function expectedCounter(attacker, defender) {
    if(attacker.type==='archer'&&dist(attacker.pos,defender.pos)>1) return 0;
    let factor=matchup(defender.type,attacker.type)*nearbyGeneralBonus(defender)*defensiveFactor(attacker.pos,attacker.owner);
    if(defender.type==='cavalry'&&terrainAt(defender.pos)==='forest') factor*=.78;
    return Math.max(15,Math.round(defender.size*.32*factor));
  }
  function battleForecast(attacker,p) {
    const owner=attacker.owner==='player'?'enemy':'player', defender=defenderAt(p,owner);
    if(!defender) return {label:'城攻め',detail:'防柵・砦・城の耐久を削ります'};
    const dealt=expectedDamage(attacker,defender,p),received=expectedCounter(attacker,defender);
    const ratio=dealt/Math.max(1,received||dealt*.25);
    const label=ratio>=2?'圧倒的有利':ratio>=1.25?'有利':ratio>=.8?'互角':ratio>=.5?'不利':'非常に危険';
    const ranged=received===0?'遠距離攻撃のため反撃なし':'双方に損害が出ます';
    return {label,detail:`${TYPES[attacker.type].name} 対 ${TYPES[defender.type].name}\n${ranged}`};
  }
  function showBattlePreview(attacker,p) {
    const forecast=battleForecast(attacker,p), modal=$('sk-modal'), secondary=$('sk-modal-secondary');
    $('sk-modal-title').textContent=forecast.label; $('sk-modal-text').textContent=forecast.detail; $('sk-modal-mark').textContent='戦';
    $('sk-modal-primary').textContent='攻撃する'; secondary.textContent='やめる'; secondary.classList.remove('is-hidden'); modal.classList.remove('is-hidden');
    secondary.onclick=()=>modal.classList.add('is-hidden');
    $('sk-modal-primary').onclick=()=>{modal.classList.add('is-hidden');attack(attacker,p);};
  }
  function attack(u,p,quiet=false) {
    const cost=foodCost(u); if(!spendFood(u.owner,cost)){ if(!quiet)log('兵糧が足りず、攻撃できない。'); return false; }
    const targetOwner=u.owner==='player'?'enemy':'player';
    const targetU=defenderAt(p,targetOwner), targetB=buildingAt(p); let damage;
    if(terrainAt(u.pos)==='forest') revealToOpponent(u);
    if(targetU) {
      const counter=Math.round(expectedCounter(u,targetU)*(.9+Math.random()*.2));
      damage=Math.round(expectedDamage(u,targetU,p)*(.9+Math.random()*.2));
      targetU.size-=damage; u.size-=counter;
      const targetDefeated=targetU.size<=0, attackerDefeated=u.size<=0;
      if(targetDefeated) state.units=state.units.filter(x=>x!==targetU);
      if(attackerDefeated) state.units=state.units.filter(x=>x!==u);
      if(!quiet) log(`${TYPES[u.type].name}が攻撃。敵に${fmt(damage)}、自軍に${fmt(counter)}の損害。${targetDefeated?' 敵部隊を撃破！':''}`);
      if(targetDefeated&&targetU.type==='general') finish(u.owner,'敵将を討ち取った');
      else if(attackerDefeated&&u.type==='general') finish(targetOwner,'総大将を討ち取られた');
    } else if(targetB) {
      const siege=u.type==='infantry'?1.25:u.type==='cavalry'?.8:u.type==='archer'?.75:1;
      damage=Math.max(100,Math.round(u.size*.7*siege*nearbyGeneralBonus(u)*(.9+Math.random()*.2))); targetB.hp-=damage;
      if(targetB.hp<=0) { state.buildings=state.buildings.filter(x=>x!==targetB); if(!quiet)log(`${BUILDINGS[targetB.type].name}を破壊！`); if(targetB.hq) finish(u.owner,'敵本陣を陥落させた'); }
      else if(!quiet) log(`${BUILDINGS[targetB.type].name}を攻撃。耐久 ${fmt(targetB.hp)}。`);
    }
    u.moved=true; state.selected=null; render(); return true;
  }

  function showStackPicker(units) {
    state.selected=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>動かす部隊を選ぶ</h3><div class="sk-option-grid">${units.map(u=>`<button class="sk-option" data-unit="${u.id}">${TYPES[u.type].mark} ${TYPES[u.type].name}<small>${fmt(u.size)}人${u.moved?'・行動済み':''}</small></button>`).join('')}</div>`;
    panel.querySelectorAll('[data-unit]').forEach(btn=>btn.onclick=()=>{state.selected=state.units.find(u=>u.id===btn.dataset.unit);closePanel();render();});
    log('同じマスにいる部隊から、動かす駒を選択。'); render();
  }

  function showRecruit() {
    state.selected=null; state.placement=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>兵種を選ぶ</h3><div class="sk-option-grid">${['infantry','cavalry','archer'].map(t=>`<button class="sk-option" data-type="${t}">${TYPES[t].name}<small>${t==='infantry'?'弓兵に強い':t==='cavalry'?'歩兵に強い・移動2':'騎兵に強い・射程2'}</small></button>`).join('')}</div><div id="sk-size-row" class="sk-size-row"></div>`;
    panel.querySelectorAll('[data-type]').forEach(btn=>btn.onclick=()=>showSizes(btn.dataset.type)); render();
  }
  function showSizes(type) {
    const row=$('sk-size-row'); row.innerHTML=[100,500,1000,5000,10000].map(size=>{const cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);return `<button data-size="${size}">${fmt(size)}人<br><small>${fmt(cost)}両</small></button>`}).join('');
    row.querySelectorAll('[data-size]').forEach(btn=>btn.onclick=()=>{
      const size=Number(btn.dataset.size), cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);
      if(state.money<cost){log('軍資金が足りません。');return;} state.placement={kind:'unit',type,size,cost}; closePanel(); log('新しい軍を置く場所を選択。'); render();
    });
  }
  function showBuild() {
    state.selected=null; state.placement=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>築くものを選ぶ</h3><div class="sk-option-grid">${Object.entries(BUILDINGS).map(([type,b])=>`<button class="sk-option" data-build="${type}">${b.name}<small>${fmt(b.cost)}両・耐久${fmt(b.hp)}</small></button>`).join('')}</div>`;
    panel.querySelectorAll('[data-build]').forEach(btn=>btn.onclick=()=>{const type=btn.dataset.build,b=BUILDINGS[type];if(state.money<b.cost){log('軍資金が足りません。');return;}state.placement={kind:'building',type,cost:b.cost};closePanel();log(`${b.name}を築く場所を選択。`);render();}); render();
  }
  function completePlacement(p) {
    const x=state.placement; if(state.money<x.cost)return;
    state.money-=x.cost;
    if(x.kind==='unit') {
      const unit={id:`p${Date.now()}`,owner:'player',type:x.type,size:x.size,pos:p,moved:true};
      state.units.push(unit); mergeSameType(unit);
    }
    else {const b=BUILDINGS[x.type];state.buildings.push({id:`p${Date.now()}`,owner:'player',type:x.type,pos:p,hp:b.hp,maxHp:b.hp});}
    log(`${x.kind==='unit'?TYPES[x.type].name:BUILDINGS[x.type].name}を配置した。`); state.placement=null; render();
  }
  function closePanel(){ $('sk-panel').classList.add('is-hidden'); $('sk-panel').innerHTML=''; }
  function cancelSelection(){ state.selected=null;state.placement=null;closePanel();render();log('選択を解除した。'); }

  function endTurn() {
    if(state.phase!=='player'||state.over)return; state.selected=null;state.placement=null;closePanel();state.phase='enemy';render();log('朱雀軍が動き始めた……');setTimeout(enemyTurn,600);
  }
  function enemyTurn() {
    state.enemyMoney+=income('enemy'); state.enemyFood+=foodIncome('enemy');
    const enemies=state.units.filter(u=>u.owner==='enemy'); enemies.forEach(u=>u.moved=false);
    for(const u of enemies) { if(state.over)break; enemyAction(u); }
    if(!state.over) enemyRecruit();
    state.turn++; state.money+=income('player'); state.food+=foodIncome('player');
    state.units.filter(u=>u.owner==='player').forEach(u=>u.moved=false); state.phase='player';
    log(`第${state.turn}ターン。城と砦から収入が届いた。`); render();
  }
  function enemyAction(u) {
    const possible=[];
    for(let p=0;p<COLS*ROWS;p++){const tu=unitsAt(p,'player').find(x=>isVisibleTo('enemy',x)),tb=buildingAt(p);if(dist(u.pos,p)<=TYPES[u.type].range&&((tu&&tu.owner==='player')||(tb&&tb.owner==='player')))possible.push(p);}
    if(possible.length){possible.sort((a,b)=>targetPriority(a)-targetPriority(b));attack(u,possible[0],true);return;}
    const hq=state.buildings.find(b=>b.owner==='player'&&b.hq); if(!hq)return;
    let steps=TYPES[u.type].move;
    while(steps--){const choices=neighbors(u.pos).filter(p=>{const occupants=unitsAt(p);return !occupants.some(x=>x.owner==='player'&&isVisibleTo('enemy',x))&&!(buildingAt(p)&&buildingAt(p).owner==='enemy')&&!(buildingAt(p)&&buildingAt(p).type==='fence');});
      if(!choices.length)break;choices.sort((a,b)=>dist(a,hq.pos)-dist(b,hq.pos));const next=choices[0];
      const ambush=unitsAt(next,'player').filter(x=>!isVisibleTo('enemy',x));if(ambush.length){ambush.forEach(revealToOpponent);attack(u,next,true);return;}
      const block=buildingAt(next);if(block&&block.owner==='player')break;u.pos=next;
    }hideAfterMove(u);u.moved=true;mergeSameType(u);
  }
  function targetPriority(p){const troops=unitsAt(p,'player'),b=buildingAt(p);if(b&&b.hq)return 0;if(troops.length===1&&troops[0].type==='general')return 1;if(troops.length)return 2;return 3;}
  function enemyRecruit(){
    const count=state.units.filter(u=>u.owner==='enemy').length;if(count>=9||state.enemyMoney<450)return;
    const type=['infantry','archer','cavalry'][Math.floor(Math.random()*3)],size=state.enemyMoney>1600?1000:500,cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);
    const spots=[...validPlacementCells('enemy','unit')];if(!spots.length||state.enemyMoney<cost)return;spots.sort((a,b)=>a-b);state.enemyMoney-=cost;const unit={id:`e${Date.now()}`,owner:'enemy',type,size,pos:spots[0],moved:true};state.units.push(unit);mergeSameType(unit);
  }
  function finish(winner,reason){state.over=true;state.phase='over';setTimeout(()=>showModal(winner==='player'?'勝鬨 — 勝利':'落城 — 敗北',`${reason}。\n${state.turn}ターンの戦いが終結した。`,winner==='player'?'勝':'敗','もう一度戦う',startGame),100);}
  function startGame(){state=freshState();$('sk-home').classList.add('is-hidden');$('sk-game').classList.remove('is-hidden');closePanel();render();}

  function bind() {
    $('sk-start').onclick=startGame;
    $('gun-home-exit').onclick=()=>location.href='/';
    $('sk-home-btn').onclick=()=>{$('sk-game').classList.add('is-hidden');$('sk-home').classList.remove('is-hidden');};
    $('sk-recruit').onclick=showRecruit;$('sk-build').onclick=showBuild;$('sk-cancel').onclick=cancelSelection;$('sk-end-turn').onclick=endTurn;
    $('sk-help').onclick=()=>showModal('遊び方','自軍の駒を選び、光るマスへ移動・攻撃します。\n同じ兵種は同じマスで合流し、兵数が加算されます。\n歩兵は弓兵に、弓兵は騎兵に、騎兵は歩兵に有利。戦闘では双方に損害が出ます。\n森に潜む敵軍は見えず、攻撃するか森を出ると姿を現します。\n軍を動かすたび兵糧を消費します。城と砦から毎ターン収入が入り、防柵は攻撃して壊すまで通れません。\n敵将または敵本陣を倒せば勝利です。','策');
  }
  const wait=setInterval(()=>{
    if ($('sk-app') && $('gun-home-exit') && $('sk-home-btn') && $('sk-end-turn') && $('sk-modal-primary') && $('sk-modal-secondary')) {
      clearInterval(wait); bind();
    }
  },50);
})();
