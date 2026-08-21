(() => {
  const COLS = 18, ROWS = 12;
  const PROVINCES = [
    {id:'katsushika',name:'葛飾区',detail:'蒼龍軍の本拠地',x:82,y:29},{id:'musashi',name:'東京都',detail:'関東攻略の中心地',x:75,y:36},
    {id:'sagami',name:'神奈川県',detail:'海と山に守られた地域',x:69,y:43},{id:'kai',name:'山梨県',detail:'騎馬軍が集う山地',x:63,y:35},
    {id:'shinano',name:'長野県',detail:'大軍がぶつかる中央山地',x:57,y:27},{id:'suruga',name:'静岡県',detail:'東海を抑える豊かな地域',x:57,y:45},
    {id:'echigo',name:'新潟県',detail:'雪と精兵の北国',x:51,y:18},{id:'owari',name:'愛知県',detail:'天下を狙う商業地',x:49,y:52},
    {id:'omi',name:'滋賀県',detail:'東西を結ぶ重要地',x:42,y:47},{id:'yamashiro',name:'京都府',detail:'日本中心へ続く最重要地',x:37,y:55},
    {id:'harima',name:'兵庫県',detail:'西日本攻略の玄関口',x:31,y:49},{id:'aki',name:'広島県',detail:'瀬戸内を支配する地域',x:25,y:57},
    {id:'sanuki',name:'香川県',detail:'四国の海上拠点',x:28,y:70},{id:'chikuzen',name:'福岡県',detail:'九州進出の足がかり',x:17,y:62},
    {id:'higo',name:'熊本県',detail:'広い平野を持つ南の大地域',x:13,y:73},{id:'satsuma',name:'鹿児島県',detail:'日本統一を決する最終戦',x:8,y:84},
  ];
  const RIVALS={suzaku:{name:'朱雀同盟',army:'朱雀軍'},genbu:{name:'玄武連邦',army:'玄武軍'},byakko:{name:'白虎軍',army:'白虎軍'}};
  function provinceFaction(province){const index=PROVINCES.findIndex(p=>p.id===province?.id);return index<=5?'suzaku':index<=10?'genbu':'byakko';}
  const TYPES = {
    general: { name: '総大将', mark: '将', move: 1, range: 1 },
    infantry: { name: '歩兵', mark: '槍', move: 1, range: 1 },
    cavalry: { name: '騎兵', mark: '騎', move: 2, range: 1 },
    archer: { name: '弓兵', mark: '弓', move: 1, range: 2 },
  };
  const TYPE_COST = { infantry: 1, cavalry: 1.5, archer: 1.2 };
  const SIZE_COST = { 100: 120, 500: 450, 1000: 800, 5000: 3400, 10000: 6000 };
  const BUILDINGS = {
    fence: { name: '防柵', cost: 450, hp: 1200, note: '最大3基・維持100両' },
    base: { name: '砦', cost: 1600, hp: 2400, money: 350, food: 500 },
    market: { name: '市場', cost: 1200, hp: 1000, money: 300, note: '毎ターン300両' },
    mine: { name: '金山', cost: 2400, hp: 1500, money: 600, note: '毎ターン600両' },
    granary: { name: '兵糧庫', cost: 1300, hp: 1200, food: 800, note: '毎ターン800俵' },
    barracks: { name: '兵舎', cost: 1800, hp: 1600, note: 'ここから軍を招集' },
    town: { name: '城下町', cost: 3800, hp: 1800, money: 1000, note:'毎ターン1,000両' },
    castle: { name: '城', cost: 3800, hp: 5000, money: 1000, food: 1600, buildable:false },
  };
  let state,profileNeedsUpload=false,profile=loadProfile(),selectedProvince=null;
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
  function initialTerritory(){const territory={};for(let r=9;r<ROWS;r++)for(let c=0;c<5;c++)territory[pos(r,c)]='player';for(let r=0;r<3;r++)for(let c=13;c<COLS;c++)territory[pos(r,c)]='enemy';return territory;}
  function loadProfile(){try{const local=JSON.parse(localStorage.getItem('gunryaku_empire')||'{}'),remote=window.GUNRYAKU_SERVER_PROFILE||{},hasRemote=Boolean(remote.updated_at);profileNeedsUpload=!hasRemote&&Object.keys(local).length>0;const saved={...{wins:0,territories:1,level:1,xp:0,command:'cavalry'},...local,...(hasRemote?remote:{})};if(!Array.isArray(saved.conquered))saved.conquered=PROVINCES.slice(0,Math.max(1,Math.min(PROVINCES.length,saved.territories||1))).map(p=>p.id);saved.territories=saved.conquered.length;return saved;}catch{return {wins:0,territories:1,level:1,xp:0,command:'cavalry',conquered:['katsushika']};}}
  function saveProfile(){profile.command='cavalry';localStorage.setItem('gunryaku_empire',JSON.stringify(profile));if(typeof emitEvent==='function')emitEvent('gunryaku_profile_save',profile);renderProfile();}
  function renderProfile(){
    if(!$('sk-wins'))return;profile.command='cavalry';const next=profile.level*100;$('sk-wins').textContent=profile.wins;$('sk-territories').textContent=profile.territories;$('sk-commander-level').textContent=profile.level;$('sk-commander-xp').textContent=profile.xp;$('sk-commander-next').textContent=next;$('sk-command-bonus').textContent=Math.round((.16+Math.min(10,profile.level)*.02)*100);
    renderCampaignMap();
  }
  function renderCampaignMap(){
    const map=$('sk-campaign-map');if(!map)return;const nextIndex=Math.min(profile.conquered.length,PROVINCES.length-1);if(!selectedProvince)selectedProvince=PROVINCES[nextIndex];
    map.innerHTML=PROVINCES.map((province,index)=>{const owned=profile.conquered.includes(province.id),available=owned||index===nextIndex,selected=selectedProvince.id===province.id,faction=provinceFaction(province);return `<button class="sk-province ${owned?'is-owned':index===nextIndex?'is-next':'is-locked'} ${owned?'':`faction-${faction}`} ${selected?'is-selected':''}" style="--x:${province.x}%;--y:${province.y}%" data-province="${province.id}" ${available?'':'disabled'}>${province.name}</button>`;}).join('');
    map.querySelectorAll('[data-province]').forEach(button=>button.onclick=()=>{selectedProvince=PROVINCES.find(p=>p.id===button.dataset.province);renderCampaignMap();});
    $('sk-unification').textContent=`${profile.conquered.length} / ${PROVINCES.length}`;$('sk-selected-province').textContent=selectedProvince.name;$('sk-selected-detail').textContent=profile.conquered.includes(selectedProvince.id)?'統治済み・再戦可能':`${RIVALS[provinceFaction(selectedProvince)].name}領 · ${selectedProvince.detail}`;
  }
  function awardVictory(province){profile.wins++;if(province&&!profile.conquered.includes(province.id))profile.conquered.push(province.id);profile.territories=profile.conquered.length;profile.xp+=100;while(profile.xp>=profile.level*100){profile.xp-=profile.level*100;profile.level++;}selectedProvince=null;saveProfile();}

  function freshState() {
    return {
      turn: 1, phase: 'player', money: 4000, food: 7000, province:selectedProvince,rival:provinceFaction(selectedProvince),territory:initialTerritory(),
      enemyMoney: 4000, enemyFood: 7000, selected: null, placement: null,
      terrain: { 22:'forest',23:'forest',24:'forest',39:'forest',40:'forest',53:'mountain',54:'mountain',55:'mountain',70:'forest',71:'forest',76:'river',94:'river',112:'river',130:'river',86:'hill',87:'hill',88:'hill',101:'forest',102:'forest',119:'forest',120:'forest',133:'mountain',134:'mountain',151:'forest',152:'forest',169:'hill',170:'hill',185:'forest',186:'forest' },
      buildings: [
        { id:'phq', owner:'player', type:'castle', pos:198, hp:6000, maxHp:6000, hq:true },
        { id:'ehq', owner:'enemy', type:'castle', pos:17, hp:6000, maxHp:6000, hq:true },
        { id:'pfence', owner:'player', type:'fence', pos:145, hp:1200, maxHp:1200 },
        { id:'efence', owner:'enemy', type:'fence', pos:70, hp:1200, maxHp:1200 },
      ],
      units: [
        { id:'pg', owner:'player', type:'general', size:1500, pos:199, moved:false },
        { id:'pi', owner:'player', type:'infantry', size:1000, pos:180, moved:false },
        { id:'pa', owner:'player', type:'archer', size:500, pos:183, moved:false },
        { id:'pc', owner:'player', type:'cavalry', size:500, pos:200, moved:false },
        { id:'eg', owner:'enemy', type:'general', size:1500, pos:16, moved:false },
        { id:'ei', owner:'enemy', type:'infantry', size:1000, pos:35, moved:false },
        { id:'ea', owner:'enemy', type:'archer', size:500, pos:15, moved:false },
        { id:'ec', owner:'enemy', type:'cavalry', size:500, pos:33, moved:false },
      ],
      revealedToPlayer: [], revealedToEnemy: [],
      log: '城から軍資金と兵糧が届いた。', over:false, animating:false,
    };
  }

  function foodCost(unit) { return Math.max(10, Math.ceil(unit.size / 100) * 4); }
  function territoryCount(owner){return Object.values(state.territory).filter(value=>value===owner).length;}
  function income(owner) {
    return state.buildings.filter(b => b.owner === owner).reduce((sum,b) => sum + (BUILDINGS[b.type].money||0), 0)+territoryCount(owner)*25;
  }
  function foodIncome(owner) {
    return state.buildings.filter(b => b.owner === owner).reduce((sum,b) => sum + (BUILDINGS[b.type].food||0), 0)+territoryCount(owner)*20;
  }
  function armyUpkeep(owner){return state.units.filter(u=>u.owner===owner).reduce((sum,u)=>sum+Math.max(3,Math.ceil(u.size/100)*3),0);}
  function troopTotal(owner,type){return state.units.filter(u=>u.owner===owner&&u.type===type).reduce((sum,u)=>sum+u.size,0);}
  function fenceCount(owner){return state.buildings.filter(b=>b.owner===owner&&b.type==='fence').length;}
  function fenceCost(owner){return BUILDINGS.fence.cost+fenceCount(owner)*300;}
  function payTurnCosts(owner){
    const foodKey=owner==='player'?'food':'enemyFood',moneyKey=owner==='player'?'money':'enemyMoney';
    const food=armyUpkeep(owner),money=fenceCount(owner)*100;state[foodKey]=Math.max(0,state[foodKey]-food);state[moneyKey]=Math.max(0,state[moneyKey]-money);
    if(state[foodKey]===0)state.units.filter(u=>u.owner===owner&&u.type!=='general').forEach(u=>u.size=Math.max(1,Math.floor(u.size*.95)));
    return {food,money};
  }
  function isVisibleTo(viewer, unit) {
    if (unit.owner === viewer || !['forest','mountain'].includes(terrainAt(unit.pos))) return true;
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
    mate.size += unit.size; mate.commander=mate.commander||unit.commander||null;mate.moved = mate.moved || unit.moved;mate.capturePos=unit.pos;mate.captureTurns=Math.max(mate.captureTurns||0,unit.captureTurns||0);
    state.units = state.units.filter(other=>other!==unit);
    return mate;
  }
  function log(message) { state.log = message; $('sk-log').textContent = message; }
  function capturePiece(unit) {
    const element=document.querySelector(`.sk-piece[data-unit="${unit.id}"]`);
    if(!element) return null;
    const rect=element.getBoundingClientRect(), clone=element.cloneNode(true);
    clone.classList.add('sk-moving-ghost');
    Object.assign(clone.style,{left:`${rect.left}px`,top:`${rect.top}px`,width:`${rect.width}px`,height:`${rect.height}px`});
    document.body.appendChild(clone);
    return {clone,rect};
  }
  function animateMove(captured,from,to,duration=620) {
    if(!captured)return Promise.resolve();
    const board=$('sk-board'),origin=board.children[from],arrival=board.children[to];
    if(origin){origin.classList.add('move-origin');setTimeout(()=>origin.classList.remove('move-origin'),850);}
    if(arrival){arrival.classList.add('move-arrival');setTimeout(()=>arrival.classList.remove('move-arrival'),780);}
    if(!arrival){captured.clone.remove();return Promise.resolve();}
    const target=arrival.getBoundingClientRect(),dx=target.left+target.width/2-(captured.rect.left+captured.rect.width/2),dy=target.top+target.height/2-(captured.rect.top+captured.rect.height/2);
    const animation=captured.clone.animate([{transform:'translate(0,0) scale(1)',opacity:1},{offset:.82,transform:`translate(${dx}px,${dy}px) scale(1.08)`,opacity:1},{transform:`translate(${dx}px,${dy}px) scale(.82)`,opacity:0}],{duration,easing:'cubic-bezier(.22,.75,.2,1)',fill:'forwards'});
    return animation.finished.catch(()=>{}).then(()=>captured.clone.remove());
  }
  function animateClash(position) {
    const cell=$('sk-board').children[position];if(!cell)return;
    cell.classList.remove('battle-clash');void cell.offsetWidth;cell.classList.add('battle-clash');setTimeout(()=>cell.classList.remove('battle-clash'),600);
  }
  function showModal(title, text, mark='軍', button='閉じる', callback=null) {
    $('sk-modal-title').textContent = title; $('sk-modal-text').textContent = text; $('sk-modal-mark').textContent = mark;
    $('sk-modal-secondary').classList.add('is-hidden');
    $('sk-modal-primary').textContent = button; $('sk-modal').classList.remove('is-hidden');
    $('sk-modal-primary').onclick = () => { $('sk-modal').classList.add('is-hidden'); if (callback) callback(); };
  }

  function render() {
    $('sk-turn').textContent = state.turn; $('sk-phase').textContent = state.phase === 'player' ? 'あなたの軍議' : '敵軍進行中';
    $('sk-money').textContent = fmt(state.money); $('sk-food').textContent = fmt(state.food); $('sk-income').textContent = `+${fmt(income('player'))}`; $('sk-upkeep').textContent = `-${fmt(armyUpkeep('player'))}`;
    $('sk-player-status').textContent=`蒼牙 Lv.${profile.level} · ${TYPES[profile.command].name}指揮`;
    $('sk-enemy-status').textContent=`${state.province?.name||'武蔵'}攻略戦`;
    $('sk-enemy-name').textContent=RIVALS[state.rival]?.army||'朱雀軍';
    for(const owner of ['player','enemy'])for(const type of ['general','infantry','cavalry','archer'])$(`sk-${owner}-${type}`).textContent=fmt(troopTotal(owner,type));
    const board = $('sk-board'); board.innerHTML = '';
    const targets = getTargets();
    for (let p=0; p<COLS*ROWS; p++) {
      const cell = document.createElement('button'); cell.type='button'; cell.className=`sk-cell terrain-${terrainAt(p)}`;
      const territoryOwner=state.territory[p];if(territoryOwner){cell.classList.add(`territory-${territoryOwner}`);const [r,c]=rc(p),same=n=>state.territory[n]===territoryOwner;if(r===0||!same(pos(r-1,c)))cell.classList.add('border-n');if(r===ROWS-1||!same(pos(r+1,c)))cell.classList.add('border-s');if(c===0||!same(pos(r,c-1)))cell.classList.add('border-w');if(c===COLS-1||!same(pos(r,c+1)))cell.classList.add('border-e');}
      if (targets.move.has(p) || targets.place.has(p)) cell.classList.add('target');
      if (targets.attack.has(p)) cell.classList.add('attack-target');
      if (state.selected && state.selected.pos === p) cell.classList.add('selected');
      const b = buildingAt(p), stack = unitsAt(p).filter(u=>isVisibleTo('player',u)); if(stack.length)cell.classList.add('has-stack');
      if (b) cell.insertAdjacentHTML('beforeend', `<span class="sk-building ${b.type} ${b.owner}" title="${BUILDINGS[b.type].name}"></span>`);
      if (stack.length) cell.insertAdjacentHTML('beforeend', `<span class="sk-unit-stack count-${Math.min(stack.length,4)}">${stack.map((u,i)=>`<span data-unit="${u.id}" class="sk-piece slot-${i+1} ${u.owner} ${u.moved?'moved':''} ${u.commander?'commander-unit':''}">${u.commander?'<span class="commander-sprite"></span>':`<span class="crest">${TYPES[u.type].mark}</span>`}<span class="troops">${fmt(u.size)}</span></span>`).join('')}</span>`);
      cell.onclick = () => onCell(p); board.appendChild(cell);
    }
    renderSelection();
    saveBattleState();
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
    const occupying=state.territory[u.pos]!==u.owner?`領土化まであと${Math.max(1,2-(u.captureTurns||0))}ターン`:null;
    box.innerHTML=`<span class="sk-selection-icon">${t.mark}</span><div><small>${t.name}</small><strong>${fmt(u.size)}人　兵糧 ${fmt(foodCost(u))}</strong><p>${occupying|| (u.moved?'このターンは行動済み':'金色＝移動　赤色＝攻撃')}</p></div>`;
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
        const hostileFort=b&&b.owner!==unit.owner&&!['market','mine','granary','town'].includes(b.type);
        if(visibleEnemy || hostileFort || (b && b.type==='fence'&&b.owner!==unit.owner)) continue;
        out.add(n); if(!occupants.length&&!['mountain','river'].includes(terrainAt(n))) frontier.push({p:n,d:d+1});
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
      ? state.buildings.filter(b => b.owner === owner && (b.type === 'castle' || b.type === 'base' || b.type === 'barracks'))
      : [...state.units.filter(u=>u.owner===owner),...state.buildings.filter(b=>b.owner===owner)];
    const cells=new Set(); anchors.forEach(a=>neighbors(a.pos).forEach(p=>{
      const occupants=unitsAt(p), building=buildingAt(p);
      if(kind==='unit') {
        const type=state.placement?.type;
        if((!building || building.owner===owner) && !occupants.some(u=>u.owner!==owner)) cells.add(p);
      } else if(!occupants.length&&!building&&state.territory[p]===owner) cells.add(p);
    })); return cells;
  }

  function onCell(p) {
    if(state.over || state.phase!=='player' || state.animating) return;
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
    const from=u.pos,captured=capturePiece(u); state.animating=true;
    hideAfterMove(u); u.pos=p;u.capturePos=p;u.captureTurns=0;u.moved=true; const combined=mergeSameType(u); state.selected=null;
    const merged=combined!==u?' 同兵種と合流した。':'';
    log(`${TYPES[combined.type].name} ${fmt(combined.size)}人が進軍。兵糧を${fmt(cost)}消費。${merged}`); render();
    animateMove(captured,from,p,680).finally(()=>{state.animating=false;render();});
  }
  function matchup(att,def) {
    if(att==='infantry'&&def==='archer')return 1.35; if(att==='archer'&&def==='cavalry')return 1.35; if(att==='cavalry'&&def==='infantry')return 1.35;
    if(def==='infantry'&&att==='archer')return .75; if(def==='archer'&&att==='cavalry')return .75; if(def==='cavalry'&&att==='infantry')return .75; return 1;
  }
  function nearbyGeneralBonus(unit) {
    const led=state.units.some(other=>other.owner===unit.owner&&other.type==='general'&&dist(other.pos,unit.pos)<=1);if(!led)return 1;
    if(unit.owner==='player'&&unit.type===profile.command)return 1.16+Math.min(10,profile.level)*.02;
    return 1.12;
  }
  function commanderBonus(unit){
    if(unit.owner==='player'&&unit.commander==='soga'&&unit.type==='cavalry')return 1.16+Math.min(10,profile.level)*.02;
    return 1;
  }
  function defensiveFactor(p, owner) {
    let factor=terrainAt(p)==='forest'?.82:terrainAt(p)==='hill'?.88:1;
    const building=buildingAt(p);
    if(building&&building.owner===owner) factor*=building.type==='castle'?.66:building.type==='base'?.78:1;
    return factor;
  }
  function expectedDamage(attacker, defender, targetPos) {
    let factor=matchup(attacker.type,defender.type)*nearbyGeneralBonus(attacker)*commanderBonus(attacker)*defensiveFactor(targetPos,defender.owner);
    if(attacker.type==='cavalry'&&['forest','mountain'].includes(terrainAt(attacker.pos))) factor*=.78;
    return Math.max(20,Math.round(attacker.size*.46*factor));
  }
  function expectedCounter(attacker, defender) {
    if(attacker.type==='archer'&&dist(attacker.pos,defender.pos)>1) return 0;
    let factor=matchup(defender.type,attacker.type)*nearbyGeneralBonus(defender)*commanderBonus(defender)*defensiveFactor(attacker.pos,attacker.owner);
    if(defender.type==='cavalry'&&['forest','mountain'].includes(terrainAt(defender.pos))) factor*=.78;
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
    const from=u.pos,captured=capturePiece(u);
    const lockPlayer=state.phase==='player'&&u.owner==='player';if(lockPlayer)state.animating=true;
    const targetOwner=u.owner==='player'?'enemy':'player';
    const targetU=defenderAt(p,targetOwner), targetB=buildingAt(p); let damage,advanced=false;
    if(['forest','mountain'].includes(terrainAt(u.pos))) revealToOpponent(u);
    if(targetU) {
      const counter=Math.round(expectedCounter(u,targetU)*(.9+Math.random()*.2));
      damage=Math.round(expectedDamage(u,targetU,p)*(.9+Math.random()*.2));
      targetU.size-=damage; u.size-=counter;
      const targetDefeated=targetU.size<=0, attackerDefeated=u.size<=0;
      if(targetDefeated) state.units=state.units.filter(x=>x!==targetU);
      if(attackerDefeated) state.units=state.units.filter(x=>x!==u);
      if(targetDefeated&&!attackerDefeated&&TYPES[u.type].range===1&&!targetB){u.pos=p;u.capturePos=p;u.captureTurns=0;advanced=true;}
      if(!quiet) log(`${TYPES[u.type].name}が攻撃。敵に${fmt(damage)}、自軍に${fmt(counter)}の損害。${targetDefeated?' 敵部隊を撃破！':''}${advanced?' そのまま敵マスへ前進。':''}`);
      if(targetDefeated&&targetU.type==='general') finish(u.owner,'敵将を討ち取った');
      else if(attackerDefeated&&u.type==='general') finish(targetOwner,'総大将を討ち取られた');
    } else if(targetB) {
      const siege=u.type==='infantry'?1.25:u.type==='cavalry'?.8:u.type==='archer'?.75:1;
      damage=Math.max(100,Math.round(u.size*.7*siege*nearbyGeneralBonus(u)*(.9+Math.random()*.2))); targetB.hp-=damage;
      if(targetB.hp<=0) { state.buildings=state.buildings.filter(x=>x!==targetB); if(!quiet)log(`${BUILDINGS[targetB.type].name}を破壊！`); if(targetB.hq) finish(u.owner,'敵本陣を陥落させた'); }
      else if(!quiet) log(`${BUILDINGS[targetB.type].name}を攻撃。耐久 ${fmt(targetB.hp)}。`);
    }
    u.moved=true;if(advanced)mergeSameType(u);state.selected=null; render();
    const resting=document.querySelector(`.sk-piece[data-unit="${u.id}"]`);if(resting)resting.style.opacity='0';
    animateMove(captured,from,p,440).then(()=>{animateClash(p);return waitMs(260);}).finally(()=>{if(lockPlayer){state.animating=false;}render();});
    return true;
  }

  function showStackPicker(units) {
    state.selected=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>動かす部隊を選ぶ</h3><div class="sk-option-grid">${units.map(u=>`<button class="sk-option" data-unit="${u.id}">${TYPES[u.type].mark} ${TYPES[u.type].name}<small>${fmt(u.size)}人${u.moved?'・行動済み':''}</small></button>`).join('')}</div>`;
    panel.querySelectorAll('[data-unit]').forEach(btn=>btn.onclick=()=>{state.selected=state.units.find(u=>u.id===btn.dataset.unit);closePanel();render();});
    log('同じマスにいる部隊から、動かす駒を選択。'); render();
  }

  function showRecruit() {
    if(state.phase!=='player'||state.animating||state.over)return;
    state.selected=null; state.placement=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>兵種を選ぶ</h3><div class="sk-option-grid">${['infantry','cavalry','archer'].map(t=>`<button class="sk-option" data-type="${t}">${TYPES[t].name}<small>${t==='infantry'?'弓兵に強い':t==='cavalry'?'歩兵に強い・移動2':'騎兵に強い・射程2'}</small></button>`).join('')}</div><div id="sk-size-row" class="sk-size-row"></div>`;
    panel.querySelectorAll('[data-type]').forEach(btn=>btn.onclick=()=>showSizes(btn.dataset.type)); render();
  }
  function showSizes(type) {
    const row=$('sk-size-row'); row.innerHTML=[100,500,1000,5000,10000].map(size=>{const cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);return `<button data-size="${size}">${fmt(size)}人<br><small>${fmt(cost)}両</small></button>`}).join('');
    row.querySelectorAll('[data-size]').forEach(btn=>btn.onclick=()=>{
      const size=Number(btn.dataset.size), cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);
      if(state.money<cost){log('軍資金が足りません。');return;}
      if(type==='cavalry'&&!state.units.some(unit=>unit.owner==='player'&&unit.commander==='soga')){showCommanderChoice(type,size,cost);return;}
      beginUnitPlacement(type,size,cost,null);
    });
  }
  function beginUnitPlacement(type,size,cost,commander){state.placement={kind:'unit',type,size,cost,commander};closePanel();log(commander?'蒼牙を率いる騎馬軍の配置先を選択。':'新しい軍を置く場所を選択。');render();}
  function showCommanderChoice(type,size,cost){
    const modal=$('sk-modal'),secondary=$('sk-modal-secondary');$('sk-modal-title').textContent='武将を配属';$('sk-modal-text').textContent=`蒼牙をこの${fmt(size)}人の騎馬軍に配属しますか？\n固有技能「蒼騎の号令」で人数以上の戦力を発揮します。`;$('sk-modal-mark').textContent='将';$('sk-modal-primary').textContent='蒼牙を召喚';secondary.textContent='通常部隊で招集';secondary.classList.remove('is-hidden');modal.classList.remove('is-hidden');$('sk-modal-primary').onclick=()=>{modal.classList.add('is-hidden');beginUnitPlacement(type,size,cost,'soga');};secondary.onclick=()=>{modal.classList.add('is-hidden');beginUnitPlacement(type,size,cost,null);};
  }
  function showBuild() {
    if(state.phase!=='player'||state.animating||state.over)return;
    state.selected=null; state.placement=null; const panel=$('sk-panel'); panel.classList.remove('is-hidden');
    panel.innerHTML=`<h3>築くものを選ぶ</h3><div class="sk-option-grid">${Object.entries(BUILDINGS).filter(([,b])=>b.buildable!==false).map(([type,b])=>{const cost=type==='fence'?fenceCost('player'):b.cost;return `<button class="sk-option" data-build="${type}">${b.name}<small>${fmt(cost)}両・${b.note||`耐久${fmt(b.hp)}`}</small></button>`;}).join('')}</div>`;
    panel.querySelectorAll('[data-build]').forEach(btn=>btn.onclick=()=>{const type=btn.dataset.build,b=BUILDINGS[type],cost=type==='fence'?fenceCost('player'):b.cost;if(type==='fence'&&fenceCount('player')>=3){log('防柵は3基が上限です。守りたい場所を選び直してください。');closePanel();return;}if(state.money<cost){log('軍資金が足りません。');return;}state.placement={kind:'building',type,cost};closePanel();log(`${b.name}を築く場所を選択。`);render();}); render();
  }
  function completePlacement(p) {
    const x=state.placement; if(state.money<x.cost)return;
    state.money-=x.cost;
    if(x.kind==='unit') {
      const unit={id:`p${Date.now()}`,owner:'player',type:x.type,size:x.size,pos:p,moved:true,commander:x.commander||null};
      state.units.push(unit); mergeSameType(unit);
    }
    else {const b=BUILDINGS[x.type];state.buildings.push({id:`p${Date.now()}`,owner:'player',type:x.type,pos:p,hp:b.hp,maxHp:b.hp});}
    log(`${x.kind==='unit'?TYPES[x.type].name:BUILDINGS[x.type].name}を配置した。`); state.placement=null; render();
  }
  function closePanel(){ $('sk-panel').classList.add('is-hidden'); $('sk-panel').innerHTML=''; }
  function cancelSelection(){ if(state.animating)return;state.selected=null;state.placement=null;closePanel();render();log('選択を解除した。'); }
  function progressOccupation(owner){
    let claimed=0;for(const unit of state.units.filter(u=>u.owner===owner)){
      if(state.territory[unit.pos]===owner){unit.capturePos=unit.pos;unit.captureTurns=0;continue;}
      if(unit.capturePos===unit.pos)unit.captureTurns=(unit.captureTurns||0)+1;else{unit.capturePos=unit.pos;unit.captureTurns=1;}
      if(unit.captureTurns>=2){state.territory[unit.pos]=owner;unit.captureTurns=0;const captured=buildingAt(unit.pos);if(captured&&captured.owner!==owner&&!captured.hq&&captured.type!=='fence')captured.owner=owner;claimed++;}
    }return claimed;
  }

  function endTurn() {
    if(state.phase!=='player'||state.over||state.animating)return;state.lastPlayerClaim=progressOccupation('player');state.selected=null;state.placement=null;closePanel();state.phase='enemy';state.animating=true;render();log(state.lastPlayerClaim?`領土を${state.lastPlayerClaim}マス拡大！ 朱雀軍が動き始めた……`:'朱雀軍が動き始めた……');setTimeout(enemyTurn,600);
  }
  const waitMs=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  async function enemyTurn() {
    state.enemyMoney+=income('enemy'); state.enemyFood+=foodIncome('enemy');
    payTurnCosts('enemy');
    const enemies=state.units.filter(u=>u.owner==='enemy'); enemies.forEach(u=>u.moved=false);
    for(const u of enemies) {
      if(state.over)break;
      if(!state.units.includes(u))continue;
      await enemyAction(u);
      await waitMs(220);
    }
    progressOccupation('enemy');
    if(state.over){state.animating=false;render();return;}
    if(!state.over) enemyRecruit();
    state.turn++; state.money+=income('player'); state.food+=foodIncome('player');const upkeep=payTurnCosts('player');
    state.units.filter(u=>u.owner==='player').forEach(u=>u.moved=false); state.phase='player';state.animating=false;
    log(`第${state.turn}ターン。収入が届き、全軍の兵糧${fmt(upkeep.food)}俵${upkeep.money?`・防柵維持${fmt(upkeep.money)}両`:''}を支払った。`); render();
  }
  async function enemyAction(u) {
    const possible=[];
    for(let p=0;p<COLS*ROWS;p++){const tu=unitsAt(p,'player').find(x=>isVisibleTo('enemy',x)),tb=buildingAt(p);if(dist(u.pos,p)<=TYPES[u.type].range&&((tu&&tu.owner==='player')||(tb&&tb.owner==='player')))possible.push(p);}
    if(possible.length){possible.sort((a,b)=>targetPriority(a)-targetPriority(b));const target=possible[0];log(`敵${TYPES[u.type].name}が攻撃を開始！`);attack(u,target,true);await waitMs(760);return;}
    const hq=state.buildings.find(b=>b.owner==='player'&&b.hq); if(!hq)return;
    let steps=TYPES[u.type].move;
    while(steps--){const choices=neighbors(u.pos).filter(p=>{const occupants=unitsAt(p),b=buildingAt(p);return !occupants.some(x=>x.owner==='player'&&isVisibleTo('enemy',x))&&!(b&&b.owner==='enemy')&&!(b&&b.type==='fence'&&b.owner!=='enemy');});
      if(!choices.length)break;choices.sort((a,b)=>dist(a,hq.pos)-dist(b,hq.pos));const next=choices[0];
      const ambush=unitsAt(next,'player').filter(x=>!isVisibleTo('enemy',x));if(ambush.length){ambush.forEach(revealToOpponent);log('森に潜んでいた自軍が敵と遭遇！');attack(u,next,true);await waitMs(760);return;}
      const block=buildingAt(next);if(block&&block.owner==='player')break;
      const from=u.pos,captured=capturePiece(u);u.pos=next;u.capturePos=next;u.captureTurns=0;render();
      if(captured)log(`敵${TYPES[u.type].name} ${fmt(u.size)}人が進軍中……`);
      await animateMove(captured,from,next,720);await waitMs(120);if(['mountain','river'].includes(terrainAt(next)))break;
    }hideAfterMove(u);u.moved=true;mergeSameType(u);
    render();
  }
  function targetPriority(p){const troops=unitsAt(p,'player'),b=buildingAt(p);if(b&&b.hq)return 0;if(troops.length===1&&troops[0].type==='general')return 1;if(troops.length)return 2;return 3;}
  function enemyRecruit(){
    const count=state.units.filter(u=>u.owner==='enemy').length;if(count>=9||state.enemyMoney<450)return;
    const type=['infantry','archer','cavalry'][Math.floor(Math.random()*3)],size=state.enemyMoney>1600?1000:500,cost=Math.round(SIZE_COST[size]*TYPE_COST[type]);
    const spots=[...validPlacementCells('enemy','unit')];if(!spots.length||state.enemyMoney<cost)return;spots.sort((a,b)=>a-b);state.enemyMoney-=cost;const unit={id:`e${Date.now()}`,owner:'enemy',type,size,pos:spots[0],moved:true};state.units.push(unit);mergeSameType(unit);
  }
  function saveBattleState(){if(!state||state.over)return;try{localStorage.setItem('gunryaku_battle_v1',JSON.stringify(state));refreshResume();}catch{}}
  function clearBattleState(){localStorage.removeItem('gunryaku_battle_v1');refreshResume();}
  function refreshResume(){const button=$('sk-resume');if(button)button.classList.toggle('is-hidden',!localStorage.getItem('gunryaku_battle_v1'));}
  function hideScreens(){['sk-splash','sk-home','sk-roster','sk-game'].forEach(id=>$(id)?.classList.add('is-hidden'));}
  function showStageSelect(){if(state&&!state.over)saveBattleState();$('sk-modal').classList.add('is-hidden');hideScreens();$('sk-home').classList.remove('is-hidden');refreshResume();}
  function showRoster(){hideScreens();$('sk-roster').classList.remove('is-hidden');renderProfile();}
  function resumeGame(){try{state=JSON.parse(localStorage.getItem('gunryaku_battle_v1'));if(!state||state.over)throw new Error();state.animating=false;state.selected=null;state.placement=null;hideScreens();$('sk-game').classList.remove('is-hidden');closePanel();render();}catch{clearBattleState();showStageSelect();}}
  function finish(winner,reason){
    const battleProvince=state.province,captured=winner==='player'&&battleProvince&&!profile.conquered.includes(battleProvince.id)?battleProvince.name:null;state.over=true;state.phase='over';clearBattleState();if(winner==='player')awardVictory(battleProvince);setTimeout(()=>{
      const modal=$('sk-modal'),secondary=$('sk-modal-secondary');$('sk-modal-title').textContent=winner==='player'?'勝鬨 — 勝利':'落城 — 敗北';$('sk-modal-text').textContent=`${reason}。\n${state.turn}ターンの戦いが終結した。${captured?`\n${captured}を蒼龍帝国の新たな領土に加えた！`:''}`;$('sk-modal-mark').textContent=winner==='player'?'勝':'敗';$('sk-modal-primary').textContent='もう一度戦う';secondary.textContent='日本攻略マップへ';secondary.classList.remove('is-hidden');modal.classList.remove('is-hidden');$('sk-modal-primary').onclick=()=>{modal.classList.add('is-hidden');selectedProvince=battleProvince;startGame();};secondary.onclick=showStageSelect;
    },100);
  }
  function startGame(){clearBattleState();state=freshState();hideScreens();$('sk-game').classList.remove('is-hidden');closePanel();render();}

  function bind() {
    $('sk-enter').onclick=showStageSelect;$('sk-roster-btn').onclick=showRoster;$('sk-roster-back').onclick=showStageSelect;$('sk-resume').onclick=resumeGame;
    $('sk-start').onclick=startGame;
    renderProfile();refreshResume();if(profileNeedsUpload){profileNeedsUpload=false;saveProfile();}
    $('sk-home-btn').onclick=showStageSelect;
    $('sk-recruit').onclick=showRecruit;$('sk-build').onclick=showBuild;$('sk-cancel').onclick=cancelSelection;$('sk-end-turn').onclick=endTurn;
    $('sk-help').onclick=()=>showModal('遊び方','領土は1マスごとに軍資金25両と兵糧20俵を毎ターン生みます。敵の市場・金山・兵糧庫・町・兵舎は、領土化すると破壊せずそのまま奪えます。\n軍は城・砦・兵舎から招集できます。自軍の防柵があるマスは通行でき、敵の防柵は破壊が必要です。\n山と森は軍を隠し、山と川へ入るとそのターンの進軍が止まります。\n騎兵招集時に蒼牙を召喚すると、固有技能で軍の攻撃力が上昇します。\n戦場は行動のたびに自動保存されます。戦場選択へ戻ったりアプリを閉じても「戦を続ける」から再開できます。','策');
  }
  const wait=setInterval(()=>{
    if ($('sk-app') && $('sk-home-btn') && $('sk-end-turn') && $('sk-modal-primary') && $('sk-modal-secondary')) {
      clearInterval(wait); bind();
    }
  },50);
})();
