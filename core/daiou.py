"""Playable turn-based solo nation strategy rules for 大王."""
from copy import deepcopy
from datetime import datetime
import random

POLICIES={"prosper":("富国","国力と収入を伸ばす",2,0,1),"train":("訓練","兵を鍛える",0,3,0),"guard":("守備","守りを整える",0,1,3),"trade":("交易","資金を得る",3,0,1)}
NATION_SEEDS=(("暁国","均衡"),("北嶺","守備"),("蒼海","交易"),("紅蓮","拡大"),("白峰","富国"),("翠野","生存"),("紫雲","機会"),("金砂","交易"),("黒鉄","軍備"),("月影","外交"))
ROWS,COLS=6,8
CAPITALS=((0,0),(0,3),(0,7),(2,1),(2,5),(3,7),(5,0),(5,3),(5,7),(3,3))
TERRAINS=("plain","plain","forest","plain","hill","plain","river")

def _initial_map():
    capitals={p:f"n{i}" for i,p in enumerate(CAPITALS)}; cells=[]
    for row in range(ROWS):
        for col in range(COLS):
            owner=capitals.get((row,col))
            cells.append({"id":f"r{row}c{col}","row":row,"col":col,"terrain":TERRAINS[(row*5+col*3+row*col)%len(TERRAINS)],"owner":owner,"structure":"capital" if owner else None,"troops":8 if owner else 0})
    return cells

def initial_game(now=None):
    now=now or datetime.now(); nations=[]
    for i,(name,purpose) in enumerate(NATION_SEEDS):
        nations.append({"id":f"n{i}","name":name,"purpose":purpose,"territory":1,"wealth":30,"army":20,"morale":70,"walls":8,"alive":True,"actions":{"expand":0,"trade":0,"build":0,"defend":0,"battle":0}})
    return {"turn":1,"season":"春","player":"n0","nations":nations,"map":_initial_map(),"diplomacy":{},"coalition":None,"support_history":{},"log":["十の国が並び立つ大陸で、あなたの治世が始まった。"],"created_at":now.isoformat(timespec="seconds"),"updated_at":now.isoformat(timespec="seconds")}

def normalize_game(game):
    default=initial_game()
    for key,value in default.items(): game.setdefault(key,deepcopy(value))
    if not game.get("map"): game["map"]=_initial_map()
    for i,item in enumerate(game["nations"]): item.setdefault("actions",deepcopy(default["nations"][i]["actions"]))
    for cell in game["map"]:
        cell.setdefault("claim", None)
        # Older saves only recorded a scout marker. Treat it as a forward camp
        # so the save can continue under the explicit occupation flow.
        if cell.get("claim"):
            cell["claim"].setdefault("progress", 0)
            cell["claim"].setdefault("started_turn", max(1, game.get("turn", 1)-1))
            cell["troops"] = max(2, int(cell.get("troops", 0)))
    _sync(game); return game

def nation(game,nation_id): return next(x for x in game["nations"] if x["id"]==nation_id)
def map_cell(game,cell_id): return next(x for x in game["map"] if x["id"]==cell_id)
def adjacent_cells(game,source): return [x for x in game["map"] if abs(x["row"]-source["row"])+abs(x["col"]-source["col"])==1]

def relation_key(a,b): return "|".join(sorted((a,b)))
def relation(game,a,b):
    if a==b: return {"status":"self","trust":100}
    return game.setdefault("diplomacy",{}).setdefault(relation_key(a,b),{"status":"neutral","trust":50})

def diplomatic_label(game,a,b):
    return {"self":"自国","neutral":"中立","pact":"不可侵","alliance":"同盟","war":"交戦"}.get(relation(game,a,b)["status"],"中立")

def propose_alliance(game,target_id,seed=None):
    normalize_game(game); pid=game["player"]
    if target_id==pid: raise ValueError("自国とは交渉できません。")
    target=nation(game,target_id)
    if not target["alive"]: raise ValueError("この国はすでに滅亡しています。")
    rel=relation(game,pid,target_id)
    if rel["status"]=="alliance": raise ValueError("すでに同盟国です。")
    if rel["status"]=="war" and rel["trust"]<35: raise ValueError("戦の傷が深く、今は交渉に応じません。")
    player=nation(game,pid); rng=random.Random(seed if seed is not None else game["turn"]*3571+int(target_id[1:]))
    compatibility=15 if target["purpose"] in {"外交","交易","生存"} else (-10 if target["purpose"] in {"拡大","軍備"} else 0)
    power_fear=max(-10,min(20,(strength(player)-strength(target))//3))
    accepted=rel["trust"]+compatibility+power_fear+rng.randint(-12,12)>=55
    if accepted:
        rel.update(status="alliance",trust=min(100,rel["trust"]+15)); message=f"{target['name']}と同盟を結んだ。"
    else:
        rel["trust"]=max(0,rel["trust"]-3); message=f"{target['name']}は同盟を見送った。"
    game["log"]=([message]+game.get("log",[]))[:30]; game["updated_at"]=datetime.now().isoformat(timespec="seconds")
    return message

def end_alliance(game,target_id):
    normalize_game(game); pid=game["player"]
    rel=relation(game,pid,target_id)
    if rel["status"] not in {"alliance","pact"}: raise ValueError("破棄できる協定がありません。")
    rel.update(status="neutral",trust=max(0,rel["trust"]-25)); target=nation(game,target_id)
    message=f"{target['name']}との協定を破棄した。信用が低下した。"; game["log"]=([message]+game.get("log",[]))[:30]; game["updated_at"]=datetime.now().isoformat(timespec="seconds")
    return message

def request_reinforcements(game,target_id,seed=None):
    """Ask an ally to reinforce the player's weakest border territory."""
    normalize_game(game); pid=game["player"]
    ally=nation(game,target_id); rel=relation(game,pid,target_id)
    if rel["status"]!="alliance": raise ValueError("援軍を頼めるのは同盟国だけです。")
    last=int(game.setdefault("support_history",{}).get(target_id,-99))
    if game["turn"]-last<4: raise ValueError(f"{ally['name']}の軍は再編中です。あと{4-(game['turn']-last)}ターン待ってください。")
    borders=[]
    for cell in game["map"]:
        if cell["owner"]!=pid: continue
        enemies=[x for x in adjacent_cells(game,cell) if x.get("owner") not in {None,pid,target_id}]
        enemy_camps=[x for x in adjacent_cells(game,cell) if (x.get("claim") or {}).get("owner") not in {None,pid,target_id}]
        if enemies or enemy_camps: borders.append(cell)
    if not borders: raise ValueError("援軍を置くほど緊迫した国境がありません。")
    target=min(borders,key=lambda x:x["troops"])
    rng=random.Random(seed if seed is not None else game["turn"]*811+int(target_id[1:]))
    troops=2+rng.randint(0,2); target["troops"]+=troops; ally["wealth"]=max(0,ally["wealth"]-2)
    game["support_history"][target_id]=game["turn"]
    rel["trust"]=min(100,rel["trust"]+4)
    message=f"{ally['name']}の援軍{troops}が、国境の{target['id']}へ到着した。"
    game["log"]=([message]+game.get("log",[]))[:30]; game["updated_at"]=datetime.now().isoformat(timespec="seconds")
    return message

def strength(item):
    land=max(1,int(item["territory"])); cohesion=max(.58,1.08-(land-1)*.055)
    return round(item["army"]*cohesion+item["walls"]*.65+item["morale"]*.16)

def derived_identity(item):
    actions=item.get("actions",{}); labels={"expand":"開拓の国","trade":"交易の国","build":"建設の国","defend":"守りの国","battle":"武威の国"}
    if not actions or max(actions.values(),default=0)<2: return "まだ定まっていない"
    return labels[max(actions,key=actions.get)]

def perform_map_action(game,action,source_id,target_id=None,now=None,seed=None):
    normalize_game(game); pid=game["player"]; player=nation(game,pid); source=map_cell(game,source_id)
    is_player_camp=source["owner"] is None and (source.get("claim") or {}).get("owner")==pid
    if source["owner"]!=pid and not (action=="occupy" and is_player_camp):
        raise ValueError("自分の領土を選んでください。")
    rng=random.Random(seed if seed is not None else game["turn"]*104729)
    if action in {"advance","invade"}:
        if not target_id: raise ValueError("進む先を選んでください。")
        target=map_cell(game,target_id)
        if target not in adjacent_cells(game,source): raise ValueError("隣の地域へだけ進めます。")
        if source["troops"]<3: raise ValueError("この地域には進軍できる兵が足りません。")
        moving=max(2,source["troops"]//2)
        if target["owner"] is None:
            claim = target.get("claim") or {}
            if claim.get("owner") == pid:
                raise ValueError("先遣隊は到着済みです。その野営地を選び『領土化』を進めてください。")
            if claim.get("owner"):
                defender=nation(game,claim["owner"]); attack=moving+rng.randint(0,3); defence=target["troops"]+rng.randint(0,3)
                source["troops"]-=moving; player["actions"]["battle"]+=1
                if attack>defence:
                    target["troops"]=max(2,attack-defence)
                    target["claim"]={"owner":pid,"progress":0,"started_turn":game["turn"]}
                    defender["morale"]=max(15,defender["morale"]-4)
                    message=f"戦力 {attack} 対 {defence}。{defender['name']}の野営地を破り、先遣隊を置いた。"
                else:
                    target["troops"]=max(1,defence-attack); player["morale"]=max(15,player["morale"]-3)
                    message=f"戦力 {attack} 対 {defence}。{defender['name']}の野営地を崩せず退いた。"
                _advance_world(game,rng); _sync(game); game["log"]=([message]+game.get("log",[]))[:30]; game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds"); return message
            if player["wealth"]<2: raise ValueError("進出準備には軍資金が2必要です。")
            player["wealth"]-=2; source["troops"]-=moving
            target["troops"]=moving
            target["claim"]={"owner":pid,"progress":0,"started_turn":game["turn"]}
            player["actions"]["expand"]+=1
            message=f"{target['id']}へ進軍し、先遣隊が野営を始めた。次のターンから領土化できます。"
        elif target["owner"]==pid:
            source["troops"]-=moving; target["troops"]+=moving; player["actions"]["defend"]+=1; message="領国内で兵を移し、守りを整えた。"
        else:
            defender=nation(game,target["owner"]); attack=moving+rng.randint(0,3); defence=target["troops"]+(5 if target["structure"]=="fort" else 0)+rng.randint(0,3); source["troops"]-=moving; player["actions"]["battle"]+=1
            if relation(game,pid,defender["id"])["status"]=="alliance":
                source["troops"]+=moving
                raise ValueError(f"{defender['name']}は同盟国です。先に同盟を破棄する必要があります。")
            relation(game,pid,defender["id"])["status"]="war"
            if attack>defence:
                defender["morale"]=max(15,defender["morale"]-5)
                target.update(owner=pid,troops=max(2,attack-defence),claim=None)
                message=f"戦力 {attack} 対 {defence}。{defender['name']}に勝ち、地域を奪った。"
            else:
                target["troops"]=max(1,defence-attack); player["morale"]=max(15,player["morale"]-3)
                message=f"戦力 {attack} 対 {defence}。{defender['name']}の守りを崩せず、兵を退いた。"
    elif action=="occupy":
        claim=source.get("claim") or {}
        if source["owner"] is not None or claim.get("owner")!=pid:
            raise ValueError("自国の先遣隊がいる中立地を選んでください。")
        if game["turn"]<=claim.get("started_turn",0):
            raise ValueError("到着したターンには領土化できません。次のターンまで守ってください。")
        claim["progress"]=int(claim.get("progress",0))+1
        if claim["progress"]>=2:
            source.update(owner=pid,claim=None)
            player["actions"]["expand"]+=1
            message=f"{source['id']}を2ターン守り抜き、正式な領土とした。"
        else:
            message=f"{source['id']}の領土化を進めた。あと1ターン守れば自国領になる。"
    elif action in {"town","fort"}:
        if source.get("structure"): raise ValueError("ここにはすでに施設があります。")
        cost=10 if action=="town" else 8
        if player["wealth"]<cost: raise ValueError(f"建設には軍資金が{cost}必要です。")
        player["wealth"]-=cost; source["structure"]=action; player["actions"]["build"]+=1
        if action=="fort": player["actions"]["defend"]+=1
        message="町を築いた。次の季節から収入が増える。" if action=="town" else "砦を築き、国境の守りを固めた。"
    elif action=="trade":
        partners={x["owner"] for x in adjacent_cells(game,source) if x["owner"] not in {None,pid}}
        if not partners: raise ValueError("隣国と接する領土を選んでください。")
        gain=4+len(partners)*2; player["wealth"]+=gain; player["actions"]["trade"]+=1; message=f"隣国と交易し、軍資金を{gain}得た。"
    elif action=="recruit":
        if player["wealth"]<5: raise ValueError("徴兵には軍資金が5必要です。")
        player["wealth"]-=5; source["troops"]+=4; player["army"]+=4; message="兵を4集め、この地域へ置いた。"
    else: raise ValueError("行動を選んでください。")
    _advance_world(game,rng); _sync(game); game["log"]=([message]+game.get("log",[]))[:30]; game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds"); return message

def _advance_world(game,rng):
    player=nation(game,game["player"]); owned=[x for x in game["map"] if x["owner"]==player["id"]]; player["wealth"]+=len(owned)+sum(2 for x in owned if x["structure"]=="town")
    for cpu in game["nations"]:
        if cpu["id"]!=player["id"] and cpu["alive"]: _cpu_turn(game,cpu,rng)
    _consider_coalition(game,rng)
    _coalition_muster(game)
    game["turn"]+=1; game["season"]=("春","夏","秋","冬")[(game["turn"]-1)%4]

def _cpu_turn(game,cpu,rng):
    camps=[x for x in game["map"] if x.get("owner") is None and (x.get("claim") or {}).get("owner")==cpu["id"]]
    if camps:
        camp=rng.choice(camps); claim=camp["claim"]
        claim["progress"]=int(claim.get("progress",0))+1
        if claim["progress"]>=2:
            camp.update(owner=cpu["id"],claim=None); cpu["actions"]["expand"]+=1
        return
    owned=[x for x in game["map"] if x["owner"]==cpu["id"]]
    if not owned: cpu["alive"]=False; return
    cpu["wealth"]+=len(owned)+sum(2 for x in owned if x["structure"]=="town")
    frontier=[(a,b) for a in owned for b in adjacent_cells(game,a) if b["owner"]!=cpu["id"] and (b["owner"] is None or relation(game,cpu["id"],b["owner"])["status"]!="alliance")]
    coalition=game.get("coalition") or {}
    if cpu["id"] in coalition.get("members",[]):
        coalition_frontier=[pair for pair in frontier if pair[1].get("owner")==coalition.get("target") or (pair[1].get("claim") or {}).get("owner")==coalition.get("target")]
        if coalition_frontier: frontier=coalition_frontier
    if frontier and rng.random()<(0.46 if cpu["purpose"] in {"拡大","軍備","機会"} else 0.24):
        source,target=rng.choice(frontier)
        if source["troops"]>=4:
            moving=max(2,source["troops"]//2); source["troops"]-=moving
            if target["owner"] is None:
                claim=target.get("claim") or {}
                if claim.get("owner") is None:
                    target["troops"]=moving
                    target["claim"]={"owner":cpu["id"],"progress":0,"started_turn":game["turn"]}
                elif moving+rng.randint(0,3)>target["troops"]+rng.randint(0,3):
                    target["troops"]=max(2,moving-target["troops"])
                    target["claim"]={"owner":cpu["id"],"progress":0,"started_turn":game["turn"]}
                    cpu["actions"]["battle"]+=1
                else: target["troops"]=max(1,target["troops"]-max(1,moving//2))
            elif moving+rng.randint(0,3)>target["troops"]+rng.randint(0,3): target.update(owner=cpu["id"],troops=max(2,moving-target["troops"])); cpu["actions"]["battle"]+=1
    elif cpu["purpose"] in {"守備","生存"}: rng.choice(owned)["troops"]+=2; cpu["actions"]["defend"]+=1
    elif cpu["purpose"] in {"交易","富国","外交"}: cpu["wealth"]+=3; cpu["actions"]["trade"]+=1
    else: rng.choice(owned)["troops"]+=1

def _consider_coalition(game,rng):
    if game.get("coalition"): return
    alive=[x for x in game["nations"] if x["alive"]]; player=nation(game,game["player"])
    rivals=[x for x in alive if x["id"]!=player["id"]]
    average=sum(x["territory"] for x in rivals)/max(1,len(rivals))
    if player["territory"]<6 or player["territory"]<average*2.2: return
    candidates=sorted(rivals,key=lambda x:(x["purpose"] in {"生存","外交","守備"},strength(x)),reverse=True)[:3]
    if len(candidates)<2 or rng.random()>.45: return
    ids=[x["id"] for x in candidates]
    game["coalition"]={"target":player["id"],"members":ids,"formed_turn":game["turn"],"name":"合従軍"}
    for item in candidates:
        relation(game,item["id"],player["id"]).update(status="war",trust=0)
    for index,left in enumerate(ids):
        for right in ids[index+1:]:
            relation(game,left,right).update(status="alliance",trust=80)
    names="・".join(x["name"] for x in candidates)
    game["log"]=[f"急拡大を恐れた{names}が合従軍を結成した！"]+game.get("log",[])

def _coalition_muster(game):
    """Periodically gather coalition troops on borders facing the target."""
    coalition=game.get("coalition") or {}
    if not coalition or game["turn"]<=coalition.get("formed_turn",game["turn"]): return
    if (game["turn"]-coalition["formed_turn"])%3: return
    target_id=coalition["target"]; gathered=[]
    for member_id in coalition.get("members",[]):
        member=nation(game,member_id)
        borders=[cell for cell in game["map"] if cell["owner"]==member_id and any(x.get("owner")==target_id for x in adjacent_cells(game,cell))]
        if not borders: continue
        cell=min(borders,key=lambda x:x["troops"]); cell["troops"]+=2; gathered.append(member["name"])
    if gathered:
        game["log"]=[f"合従軍が国境へ集結。{'・'.join(gathered)}が兵を進めた。"]+game.get("log",[])

def _sync(game):
    for item in game["nations"]:
        item["territory"]=sum(x["owner"]==item["id"] for x in game["map"]); item["alive"]=item["territory"]>0

def apply_policy(game,policy,now=None,seed=None):
    """Legacy helper. Policies are no longer shown to players."""
    normalize_game(game)
    if policy not in POLICIES: raise ValueError("方針を選んでください。")
    p=nation(game,game["player"]); _,_,wealth,army,morale=POLICIES[policy]; p["wealth"]+=wealth+p["territory"]; p["army"]+=army; p["morale"]=min(100,p["morale"]+morale)
    if policy=="guard": p["walls"]+=2
    _advance_world(game,random.Random(seed if seed is not None else game["turn"]*7919)); game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds"); return [f"{POLICIES[policy][0]}を実行した。"]
