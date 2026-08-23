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
    return {"turn":1,"season":"春","player":"n0","nations":nations,"map":_initial_map(),"log":["十の国が並び立つ大陸で、あなたの治世が始まった。"],"created_at":now.isoformat(timespec="seconds"),"updated_at":now.isoformat(timespec="seconds")}

def normalize_game(game):
    default=initial_game()
    for key,value in default.items(): game.setdefault(key,deepcopy(value))
    if not game.get("map"): game["map"]=_initial_map()
    for i,item in enumerate(game["nations"]): item.setdefault("actions",deepcopy(default["nations"][i]["actions"]))
    _sync(game); return game

def nation(game,nation_id): return next(x for x in game["nations"] if x["id"]==nation_id)
def map_cell(game,cell_id): return next(x for x in game["map"] if x["id"]==cell_id)
def adjacent_cells(game,source): return [x for x in game["map"] if abs(x["row"]-source["row"])+abs(x["col"]-source["col"])==1]

def strength(item):
    land=max(1,int(item["territory"])); cohesion=max(.58,1.08-(land-1)*.055)
    return round(item["army"]*cohesion+item["walls"]*.65+item["morale"]*.16)

def derived_identity(item):
    actions=item.get("actions",{}); labels={"expand":"開拓の国","trade":"交易の国","build":"建設の国","defend":"守りの国","battle":"武威の国"}
    if not actions or max(actions.values(),default=0)<2: return "まだ定まっていない"
    return labels[max(actions,key=actions.get)]

def perform_map_action(game,action,source_id,target_id=None,now=None,seed=None):
    normalize_game(game); pid=game["player"]; player=nation(game,pid); source=map_cell(game,source_id)
    if source["owner"]!=pid: raise ValueError("自分の領土を選んでください。")
    rng=random.Random(seed if seed is not None else game["turn"]*104729)
    if action in {"advance","invade"}:
        if not target_id: raise ValueError("進む先を選んでください。")
        target=map_cell(game,target_id)
        if target not in adjacent_cells(game,source): raise ValueError("隣の地域へだけ進めます。")
        if source["troops"]<3: raise ValueError("この地域には進軍できる兵が足りません。")
        moving=max(2,source["troops"]//2)
        if target["owner"] is None:
            if player["wealth"]<3: raise ValueError("進出には軍資金が3必要です。")
            player["wealth"]-=3; source["troops"]-=moving; target.update(owner=pid,troops=moving); player["actions"]["expand"]+=1; message=f"{target['id']}へ進出し、新しい領土を得た。"
        elif target["owner"]==pid:
            source["troops"]-=moving; target["troops"]+=moving; player["actions"]["defend"]+=1; message="領国内で兵を移し、守りを整えた。"
        else:
            defender=nation(game,target["owner"]); attack=moving+rng.randint(0,3); defence=target["troops"]+(5 if target["structure"]=="fort" else 0)+rng.randint(0,3); source["troops"]-=moving; player["actions"]["battle"]+=1
            if attack>defence: defender["morale"]=max(15,defender["morale"]-5); target.update(owner=pid,troops=max(2,attack-defence)); message=f"{defender['name']}との戦に勝ち、地域を奪った。"
            else: target["troops"]=max(1,defence-attack); player["morale"]=max(15,player["morale"]-3); message=f"{defender['name']}の守りを崩せず、兵を退いた。"
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
    game["turn"]+=1; game["season"]=("春","夏","秋","冬")[(game["turn"]-1)%4]

def _cpu_turn(game,cpu,rng):
    owned=[x for x in game["map"] if x["owner"]==cpu["id"]]
    if not owned: cpu["alive"]=False; return
    cpu["wealth"]+=len(owned)+sum(2 for x in owned if x["structure"]=="town")
    frontier=[(a,b) for a in owned for b in adjacent_cells(game,a) if b["owner"]!=cpu["id"]]
    if frontier and rng.random()<(0.46 if cpu["purpose"] in {"拡大","軍備","機会"} else 0.24):
        source,target=rng.choice(frontier)
        if source["troops"]>=4:
            moving=max(2,source["troops"]//2); source["troops"]-=moving
            if target["owner"] is None: target.update(owner=cpu["id"],troops=moving); cpu["actions"]["expand"]+=1
            elif moving+rng.randint(0,3)>target["troops"]+rng.randint(0,3): target.update(owner=cpu["id"],troops=max(2,moving-target["troops"])); cpu["actions"]["battle"]+=1
    elif cpu["purpose"] in {"守備","生存"}: rng.choice(owned)["troops"]+=2; cpu["actions"]["defend"]+=1
    elif cpu["purpose"] in {"交易","富国","外交"}: cpu["wealth"]+=3; cpu["actions"]["trade"]+=1
    else: rng.choice(owned)["troops"]+=1

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
