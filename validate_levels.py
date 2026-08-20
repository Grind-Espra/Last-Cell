import json
from functools import lru_cache
from pathlib import Path
ROOT=Path('/mnt/data/game_work')
base=json.load(open(ROOT/'levels.json',encoding='utf-8'))
extra=json.load(open(ROOT/'extra_levels.json',encoding='utf-8'))
all_levels=base+extra
BLOCKED={'window','fireplace','candlestick','table','long_table','plant','bookcase','wardrobe'}

def satisfies(level,ch,pos):
    cells={(c['r'],c['c']):c for c in level['cells']}
    r,c=pos; cell=cells.get((r,c))
    if not cell or cell['object'] in BLOCKED: return False
    clues=[x for x in level['clues'] if x['character']==ch]
    for cl in clues:
        if 'row' in cl and r!=cl['row']: return False
        if 'col' in cl and c!=cl['col']: return False
        if 'room' in cl and cell['roomId']!=cl['room']: return False
        for kind in ('on','adj','not_adj'):
            if kind not in cl: continue
            obj=cl[kind]
            if kind=='on' and cell['object']!=obj: return False
            if kind in ('adj','not_adj'):
                neigh=[]
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    q=cells.get((r+dr,c+dc))
                    if q: neigh.append(q.get('object'))
                hit=obj in neigh
                if kind=='adj' and not hit: return False
                if kind=='not_adj' and hit: return False
    return True

def solve(level, limit=2):
    chars=level['activeCharacters']
    candidates={ch:[(r,c) for r in range(level['rows']) for c in range(level['cols']) if satisfies(level,ch,(r,c))] for ch in chars}
    # Some legacy levels encode clues in combined patterns; candidate domains can still be empty if authored inconsistently.
    if any(not d for d in candidates.values()): return [],candidates
    order=sorted(chars,key=lambda ch:len(candidates[ch]))
    sols=[]
    def bt(i,assign,used_r,used_c):
        if len(sols)>=limit: return
        if i==len(order):
            rows=set(range(level['rows']))-used_r; cols=set(range(level['cols']))-used_c
            if len(rows)==1 and len(cols)==1:
                vr,vc=next(iter(rows)),next(iter(cols)); cells={(c['r'],c['c']):c for c in level['cells']}
                vcell=cells.get((vr,vc))
                if vcell and vcell['object'] not in BLOCKED:
                    room=vcell['roomId']; inroom=[ch for ch,p in assign.items() if cells[p]['roomId']==room]
                    if len(inroom)==1 and inroom[0]==level.get('culprit'):
                        sols.append(assign.copy())
            return
        ch=order[i]
        for pos in candidates[ch]:
            r,c=pos
            if r in used_r or c in used_c: continue
            assign[ch]=pos; used_r.add(r); used_c.add(c)
            bt(i+1,assign,used_r,used_c)
            used_r.remove(r); used_c.remove(c); del assign[ch]
    bt(0,{},set(),set())
    return sols,candidates

stats=[]
for idx,l in enumerate(all_levels,1):
    sols,cands=solve(l,limit=2)
    expected={ch:tuple(map(int,p.split(','))) for ch,p in l['solution'].items()}
    found=sols[0] if sols else None
    stats.append({'id':l['id'],'solutions':len(sols),'unique':len(sols)==1,'matches':found==expected,'min_domain':min((len(v) for v in cands.values()),default=0)})

bad=[x for x in stats if not (x['unique'] and x['matches'])]
print(json.dumps({'total':len(stats),'valid':len(stats)-len(bad),'invalid':len(bad),'bad':bad[:30]},ensure_ascii=False,indent=2))
(ROOT/'validation_report_v10.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
