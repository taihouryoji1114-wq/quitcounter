"""Playable turn-based solo nation strategy rules for 大王."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import random

POLICIES={"prosper":("富国","国力と収入を伸ばす",2,0,1),"train":("訓練","兵を鍛える",0,3,0),"guard":("守備","守りを整える",0,1,3),"trade":("交易","資金を得る",3,0,1)}
NATION_SEEDS=(("暁国","均衡"),("北嶺","守備"),("蒼海","交易"),("紅蓮","拡大"),("白峰","富国"),("翠野","生存"),("紫雲","機会"),("金砂","交易"),("黒鉄","軍備"),("月影","外交"))
MAP_VERSION=4
MAP_KIND="tokyo_mainland"
COMMANDS_PER_TURN=3
_MAP_DATA=json.loads((Path(__file__).resolve().parents[1]/"static"/"daiou_tokyo_map.json").read_text())
_REGIONS={item["id"]:item for item in _MAP_DATA["regions"]}
# The player begins in 葛飾区.  The other powers are spread through the 23
# wards and Tama so no single country starts with an automatic advantage.
CAPITALS={"13122":"n0","13201":"n1","13111":"n2","13120":"n3","13112":"n4",
          "13205":"n5","13108":"n6","13209":"n7","13202":"n8","13104":"n9"}
TERRAINS=("plain","plain","forest","plain","hill","plain","river")
_ARMY_NUMERALS=("零","一","二","三","四","五","六","七","八","九","十")

def _legion_name(number):
    return f"第{_ARMY_NUMERALS[number] if number<len(_ARMY_NUMERALS) else number}軍"

def _initial_map():
    cells=[]
    for region in _MAP_DATA["regions"]:
        owner=CAPITALS.get(region["id"])
        value=3 if owner else 1+(sum(ord(ch) for ch in region["name"])%3)
        cells.append({"id":region["id"],"name":region["name"],"terrain":region["terrain"],
                      "neighbors":region["neighbors"],"owner":owner,
                      "structure":"capital" if owner else None,"troops":8 if owner else 0,
                      "value":value})
    return cells

def map_viewbox(): return _MAP_DATA["viewBox"]
def region_shape(region_id): return _REGIONS[region_id]

def initial_game(now=None):
    now=now or datetime.now(); nations=[]
    for i,(name,purpose) in enumerate(NATION_SEEDS):
        nations.append({"id":f"n{i}","name":name,"purpose":purpose,"territory":1,"wealth":30,"army":20,"morale":70,"walls":8,"alive":True,"actions":{"expand":0,"trade":0,"build":0,"defend":0,"battle":0}})
    world=_initial_map()
    legions=[{"id":f"{owner}-1","owner":owner,"name":"第一軍","location":region_id,"formed_turn":1}
             for region_id,owner in CAPITALS.items()]
    return {"version":MAP_VERSION,"map_kind":MAP_KIND,"turn":1,"season":"春","commands_left":COMMANDS_PER_TURN,
            "player":"n0","nations":nations,"map":world,"legions":legions,"diplomacy":{},"coalition":None,
            "support_history":{},"turn_events":[],"log":["葛飾の地から、あなたの治世が始まった。"],
            "created_at":now.isoformat(timespec="seconds"),"updated_at":now.isoformat(timespec="seconds")}

def normalize_game(game):
    previous_map_kind=game.get("map_kind")
    default=initial_game()
    for key,value in default.items(): game.setdefault(key,deepcopy(value))
    if previous_map_kind != MAP_KIND:
        # Never discard the former board.  It remains embedded in the save as
        # a recovery snapshot while the active campaign moves to real regions.
        if game.get("map") and not game.get("legacy_grid_map"):
            game["legacy_grid_map"]=deepcopy(game["map"])
        game["map"]=_initial_map()
        game["log"]=["旧天下盤を保存し、葛飾から実在地域で再出発した。"]+game.get("log",[])
    if not game.get("map"): game["map"]=_initial_map()
    game.update(version=MAP_VERSION,map_kind=MAP_KIND)
    for i,item in enumerate(game["nations"]): item.setdefault("actions",deepcopy(default["nations"][i]["actions"]))
    for cell in game["map"]:
        region=_REGIONS.get(cell["id"],{})
        cell.setdefault("name",region.get("name",cell["id"]))
        cell.setdefault("neighbors",region.get("neighbors",[]))
        cell.setdefault("claim", None)
        cell.setdefault("value", 1+(sum(ord(ch) for ch in cell.get("name",cell["id"]))%3))
        # Older saves only recorded a scout marker. Treat it as a forward camp
        # so the save can continue under the explicit occupation flow.
        if cell.get("claim"):
            cell["claim"].setdefault("progress", 0)
            cell["claim"].setdefault("started_turn", max(1, game.get("turn", 1)-1))
            cell["claim"].setdefault("last_progress_turn", 0)
            cell["troops"] = max(2, int(cell.get("troops", 0)))
    valid_ids={cell["id"] for cell in game["map"]}
    game["legions"]=[legion for legion in game.get("legions",[]) if legion.get("location") in valid_ids
                     and nation(game,legion.get("owner"))["alive"]
                     and (map_cell(game,legion["location"]).get("owner")==legion.get("owner")
                          or (map_cell(game,legion["location"]).get("claim") or {}).get("owner")==legion.get("owner"))]
    _sync(game); return game

def nation(game,nation_id): return next(x for x in game["nations"] if x["id"]==nation_id)
def map_cell(game,cell_id): return next(x for x in game["map"] if x["id"]==cell_id)
def legion_at(game,cell_id):
    return next((item for item in game.get("legions",[]) if item.get("location")==cell_id),None)

def _relocate_legion(game,source_id,target_id):
    moving=legion_at(game,source_id); standing=legion_at(game,target_id)
    if not moving: return
    if standing and standing["id"]!=moving["id"]:
        game["legions"].remove(moving)
    else: moving["location"]=target_id

def _clear_legions(game,owner_id):
    game["legions"]=[item for item in game.get("legions",[]) if item.get("owner")!=owner_id]

def form_legion(game,cell_id,now=None):
    """Turn a garrison into a named field army without duplicating its troops."""
    normalize_game(game); pid=game["player"]; cell=map_cell(game,cell_id)
    if cell.get("owner")!=pid: raise ValueError("自国領で軍団を編成してください。")
    if cell.get("troops",0)<5: raise ValueError("軍団の編成には兵5以上が必要です。")
    if legion_at(game,cell_id): raise ValueError("この地域にはすでに軍団がいます。")
    owned=[item for item in game.get("legions",[]) if item.get("owner")==pid]
    number=max([int(item["id"].rsplit("-",1)[-1]) for item in owned if item.get("id","").rsplit("-",1)[-1].isdigit()] or [0])+1
    name=_legion_name(number)
    game["legions"].append({"id":f"{pid}-{number}","owner":pid,"name":name,"location":cell_id,"formed_turn":game["turn"]})
    return _spend_command(game,f"{cell['name']}で{name}を編成した。",now)
def adjacent_cells(game,source):
    neighbor_ids=set(source.get("neighbors",[]))
    return [x for x in game["map"] if x["id"] in neighbor_ids]

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

def _tactical_attack_bonus(game,source,target,tactic,pid):
    labels={"direct":"正面攻撃","pincer":"挟撃"}
    if tactic not in labels: raise ValueError("戦い方を選んでください。")
    if tactic=="pincer":
        fronts=sum(cell.get("owner")==pid for cell in adjacent_cells(game,target))
        if fronts<2: raise ValueError("挟撃には、敵地へ接する自国領が2か所以上必要です。")
        return 3+(fronts-2)*2,labels[tactic]
    return 0,labels[tactic]

def region_income(cell):
    """Seasonal income makes some land worth fighting for."""
    return int(cell.get("value",1))+(2 if cell.get("structure") in {"town","capital"} else 0)

def terrain_effect(cell):
    return {"forest":"守備 +1","hill":"守備 +2","river":"守備 +1","plain":"進軍向き"}.get(cell.get("terrain"),"平地")

def _capital_surrender(game,winner_id,loser_id):
    """Taking a capital ends that country and transfers its remaining realm."""
    captured=0
    for cell in game["map"]:
        if cell.get("owner")==loser_id:
            cell["owner"]=winner_id; cell["troops"]=max(1,cell.get("troops",0)//2); captured+=1
        claim=cell.get("claim") or {}
        if claim.get("owner")==loser_id:
            cell["claim"]=None; cell["troops"]=0
    loser=nation(game,loser_id); loser["alive"]=False; loser["territory"]=0
    _clear_legions(game,loser_id)
    return captured

def _spend_command(game,message,now):
    game["commands_left"]=max(0,int(game.get("commands_left",COMMANDS_PER_TURN))-1)
    _sync(game); game["log"]=([message]+game.get("log",[]))[:30]
    game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds")
    return message

def perform_map_action(game,action,source_id,target_id=None,now=None,seed=None,tactic="direct",march_troops=None):
    normalize_game(game); pid=game["player"]; player=nation(game,pid); source=map_cell(game,source_id)
    if int(game.get("commands_left",COMMANDS_PER_TURN))<=0:
        raise ValueError("今季の軍令は使い切りました。『季節を進める』を押してください。")
    is_player_camp=source["owner"] is None and (source.get("claim") or {}).get("owner")==pid
    if source["owner"]!=pid and not (action=="occupy" and is_player_camp):
        raise ValueError("自分の領土を選んでください。")
    rng=random.Random(seed if seed is not None else game["turn"]*104729)
    if action=="transfer":
        if not target_id: raise ValueError("兵を移す自国領を選んでください。")
        target=map_cell(game,target_id)
        if target["id"]==source["id"]: raise ValueError("別の自国領を選んでください。")
        if target.get("owner")!=pid: raise ValueError("兵の移動先は自国領だけです。")
        if source["troops"]<2: raise ValueError("この地域には移動できる兵がいません。")
        moving=max(1,source["troops"]//2) if march_troops is None else int(march_troops)
        moving=min(moving,source["troops"]-1)
        if moving<1: raise ValueError("移動する兵数を選んでください。")
        source["troops"]-=moving; target["troops"]+=moving
        _relocate_legion(game,source_id,target_id); player["actions"]["defend"]+=1
        message=f"{source['name']}から{target['name']}へ兵{moving}を移動した。"
    elif action in {"advance","invade"}:
        if not target_id: raise ValueError("進む先を選んでください。")
        target=map_cell(game,target_id)
        if target not in adjacent_cells(game,source): raise ValueError("隣の地域へだけ進めます。")
        if source["troops"]<3: raise ValueError("この地域には進軍できる兵が足りません。")
        moving=max(2,source["troops"]//2) if march_troops is None else int(march_troops)
        moving=min(moving,source["troops"]-1)
        if moving<2: raise ValueError("進軍には2以上の兵が必要です。")
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
                    _relocate_legion(game,source_id,target_id)
                    message=f"戦力 {attack} 対 {defence}。{defender['name']}の野営地を破り、先遣隊を置いた。"
                else:
                    target["troops"]=max(1,defence-attack); player["morale"]=max(15,player["morale"]-3)
                    message=f"戦力 {attack} 対 {defence}。{defender['name']}の野営地を崩せず退いた。"
                return _spend_command(game,message,now)
            if player["wealth"]<2: raise ValueError("進出準備には軍資金が2必要です。")
            player["wealth"]-=2; source["troops"]-=moving
            target["troops"]=moving
            target["claim"]={"owner":pid,"progress":0,"started_turn":game["turn"]}
            _relocate_legion(game,source_id,target_id)
            player["actions"]["expand"]+=1
            message=f"{target.get('name',target['id'])}へ進軍し、先遣隊が野営を始めた。次のターンから領土化できます。"
        elif target["owner"]==pid:
            source["troops"]-=moving; target["troops"]+=moving; _relocate_legion(game,source_id,target_id); player["actions"]["defend"]+=1; message="領国内で兵を移し、守りを整えた。"
        else:
            defender=nation(game,target["owner"])
            if relation(game,pid,defender["id"])["status"]=="alliance":
                source["troops"]-=moving; target["troops"]+=moving
                player["actions"]["defend"]+=1
                relation(game,pid,defender["id"])["trust"]=min(100,relation(game,pid,defender["id"])["trust"]+3)
                _relocate_legion(game,source_id,target_id)
                message=f"{defender['name']}の{target['name']}へ援軍{moving}を派遣した。"
                return _spend_command(game,message,now)
            bonus,tactic_label=_tactical_attack_bonus(game,source,target,tactic,pid)
            overreach=max(0,(player.get("territory",1)-4)//3)
            terrain_defence={"forest":1,"hill":2,"river":1}.get(target.get("terrain"),0)
            structure_defence={"fort":5,"capital":8}.get(target.get("structure"),0)
            attack=max(1,moving+bonus-overreach+rng.randint(0,3)); defence=target["troops"]+structure_defence+terrain_defence+rng.randint(0,3); source["troops"]-=moving; player["actions"]["battle"]+=1
            relation(game,pid,defender["id"])["status"]="war"
            if attack>defence:
                defender["morale"]=max(15,defender["morale"]-5)
                was_capital=target.get("structure")=="capital"
                target.update(owner=pid,troops=max(2,attack-defence),claim=None)
                _relocate_legion(game,source_id,target_id)
                if was_capital:
                    lands=_capital_surrender(game,pid,defender["id"])
                    message=f"{tactic_label}！ 戦力 {attack} 対 {defence}。{defender['name']}の本城を落とし、残る{lands}地域が降伏した。"
                else: message=f"{tactic_label}！ 戦力 {attack} 対 {defence}。{defender['name']}に勝ち、地域を奪った。"
            else:
                target["troops"]=max(1,defence-attack); player["morale"]=max(15,player["morale"]-3)
                message=f"{tactic_label}。戦力 {attack} 対 {defence}。{defender['name']}の守りを崩せず、兵を退いた。"
    elif action=="occupy":
        claim=source.get("claim") or {}
        if source["owner"] is not None or claim.get("owner")!=pid:
            raise ValueError("自国の先遣隊がいる中立地を選んでください。")
        if game["turn"]<=claim.get("started_turn",0):
            raise ValueError("到着したターンには領土化できません。次のターンまで守ってください。")
        if claim.get("last_progress_turn")==game["turn"]:
            raise ValueError("この季節の領土化は進めました。次の季節まで守ってください。")
        claim["progress"]=int(claim.get("progress",0))+1
        claim["last_progress_turn"]=game["turn"]
        if claim["progress"]>=2:
            source.update(owner=pid,claim=None)
            player["actions"]["expand"]+=1
            message=f"{source.get('name',source['id'])}を2ターン守り抜き、正式な領土とした。"
        else:
            message=f"{source.get('name',source['id'])}の領土化を進めた。あと1ターン守れば自国領になる。"
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
    return _spend_command(game,message,now)

def end_turn(game,now=None,seed=None):
    """Resolve every rival after the player has finished planning the season."""
    normalize_game(game)
    old_turn=game["turn"]
    rng=random.Random(seed if seed is not None else old_turn*65537)
    _advance_world(game,rng)
    game["commands_left"]=COMMANDS_PER_TURN
    _sync(game)
    message=f"第{old_turn}季の軍議を終え、諸国が動いた。第{game['turn']}季・{game['season']}へ。"
    game["log"]=([message]+game.get("log",[]))[:30]
    game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds")
    return message

def _advance_world(game,rng):
    game["turn_events"]=[]
    player=nation(game,game["player"]); owned=[x for x in game["map"] if x["owner"]==player["id"]]
    player["wealth"]+=sum(region_income(x) for x in owned)-sum(x["troops"] for x in owned)//30
    for cpu in game["nations"]:
        if cpu["id"]==player["id"] or not cpu["alive"]: continue
        cpu_owned=[x for x in game["map"] if x["owner"]==cpu["id"]]
        cpu["wealth"]+=sum(region_income(x) for x in cpu_owned)-sum(x["troops"] for x in cpu_owned)//30
        orders=3 if cpu["purpose"] in {"拡大","軍備","機会"} else 2
        for _ in range(orders):
            if cpu["alive"]: _cpu_turn(game,cpu,rng)
    _consider_coalition(game,rng)
    _coalition_muster(game)
    game["turn"]+=1; game["season"]=("春","夏","秋","冬")[(game["turn"]-1)%4]

def _cpu_turn(game,cpu,rng):
    camps=[x for x in game["map"] if x.get("owner") is None and (x.get("claim") or {}).get("owner")==cpu["id"]]
    eligible_camps=[camp for camp in camps if game["turn"]>camp["claim"].get("started_turn",0) and camp["claim"].get("last_progress_turn")!=game["turn"]]
    if eligible_camps:
        camp=rng.choice(eligible_camps); claim=camp["claim"]
        claim["progress"]=int(claim.get("progress",0))+1
        claim["last_progress_turn"]=game["turn"]
        if claim["progress"]>=2:
            camp.update(owner=cpu["id"],claim=None); cpu["actions"]["expand"]+=1
        return
    owned=[x for x in game["map"] if x["owner"]==cpu["id"]]
    if not owned: cpu["alive"]=False; return
    frontier=[(a,b) for a in owned for b in adjacent_cells(game,a) if b["owner"]!=cpu["id"] and (b["owner"] is None or relation(game,cpu["id"],b["owner"])["status"]!="alliance")]
    coalition=game.get("coalition") or {}
    if cpu["id"] in coalition.get("members",[]):
        coalition_frontier=[pair for pair in frontier if pair[1].get("owner")==coalition.get("target") or (pair[1].get("claim") or {}).get("owner")==coalition.get("target")]
        if coalition_frontier: frontier=coalition_frontier
    threatened=[cell for cell in owned if any(x.get("owner") not in {None,cpu["id"]} for x in adjacent_cells(game,cell))]
    if threatened and cpu["wealth"]>=5 and min(x["troops"] for x in threatened)<7 and rng.random()<.46:
        cell=min(threatened,key=lambda x:x["troops"]); cpu["wealth"]-=5; cell["troops"]+=4; cpu["actions"]["defend"]+=1; return
    if threatened and cpu["wealth"]>=8 and rng.random()<.16:
        choices=[x for x in threatened if not x.get("structure")]
        if choices:
            cpu["wealth"]-=8; rng.choice(choices)["structure"]="fort"; cpu["actions"]["build"]+=1; return
    advance_chance=.72 if cpu["purpose"] in {"拡大","軍備","機会"} else (.52 if cpu["purpose"] in {"均衡","守備","生存"} else .42)
    if frontier and rng.random()<advance_chance:
        source,target=rng.choice(frontier)
        if source["troops"]>=4:
            moving=max(2,source["troops"]//2); source["troops"]-=moving
            if target["owner"] is None:
                claim=target.get("claim") or {}
                if claim.get("owner") is None:
                    target["troops"]=moving
                    target["claim"]={"owner":cpu["id"],"progress":0,"started_turn":game["turn"]}
                    _relocate_legion(game,source["id"],target["id"])
                elif moving+rng.randint(0,3)>target["troops"]+rng.randint(0,3):
                    attacked_player=(target.get("claim") or {}).get("owner")==game["player"]
                    target["troops"]=max(2,moving-target["troops"])
                    target["claim"]={"owner":cpu["id"],"progress":0,"started_turn":game["turn"]}
                    _relocate_legion(game,source["id"],target["id"])
                    cpu["actions"]["battle"]+=1
                    if attacked_player:
                        game["turn_events"].append({"kind":"enemy_attack","result":"lost","attacker":cpu["name"],"target":target["name"],"message":f"{cpu['name']}軍が{target['name']}の野営地を襲撃。先遣隊が敗れ、野営地を奪われました。"})
                else: target["troops"]=max(1,target["troops"]-max(1,moving//2))
            else:
                defender_id=target["owner"]
                defence=target["troops"]+{"fort":5,"capital":8}.get(target.get("structure"),0)+{"forest":1,"hill":2,"river":1}.get(target.get("terrain"),0)+rng.randint(0,3)
                attack=moving+rng.randint(0,3)
                if attack>defence:
                    was_capital=target.get("structure")=="capital"
                    target.update(owner=cpu["id"],troops=max(2,attack-defence),claim=None); cpu["actions"]["battle"]+=1
                    _relocate_legion(game,source["id"],target["id"])
                    if was_capital: _capital_surrender(game,cpu["id"],defender_id)
                    if defender_id==game["player"]:
                        outcome="本城が陥落しました。" if was_capital else "守備隊が敗れ、領土を奪われました。"
                        game["turn_events"].append({"kind":"enemy_attack","result":"lost","attacker":cpu["name"],"target":target["name"],"attack":attack,"defence":defence,"message":f"{cpu['name']}軍が{target['name']}へ侵攻。戦力 {attack} 対 {defence}。{outcome}"})
                else: target["troops"]=max(1,defence-attack)
                if attack<=defence and defender_id==game["player"]:
                    game["turn_events"].append({"kind":"enemy_attack","result":"defended","attacker":cpu["name"],"target":target["name"],"attack":attack,"defence":defence,"message":f"{cpu['name']}軍が{target['name']}へ侵攻。戦力 {attack} 対 {defence}。守備隊が撃退しました。"})
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
        owned=[x for x in game["map"] if x["owner"]==item["id"]]
        item["territory"]=len(owned); item["army"]=sum(x.get("troops",0) for x in owned); item["alive"]=item["territory"]>0

def apply_policy(game,policy,now=None,seed=None):
    """Legacy helper. Policies are no longer shown to players."""
    normalize_game(game)
    if policy not in POLICIES: raise ValueError("方針を選んでください。")
    p=nation(game,game["player"]); _,_,wealth,army,morale=POLICIES[policy]; p["wealth"]+=wealth+p["territory"]; p["army"]+=army; p["morale"]=min(100,p["morale"]+morale)
    if policy=="guard": p["walls"]+=2
    _advance_world(game,random.Random(seed if seed is not None else game["turn"]*7919)); game["updated_at"]=(now or datetime.now()).isoformat(timespec="seconds"); return [f"{POLICIES[policy][0]}を実行した。"]
