"""Durable external-practice history import and future scheduler submissions."""
import json,os,time
from pathlib import Path
from datetime import datetime,timezone
import anki_bridge as bridge
JOURNAL=Path(__file__).resolve().parent/'anki-reviews.json'
def load(): return json.loads(JOURNAL.read_text())
def save(journal):
    temp=JOURNAL.with_suffix('.tmp');temp.write_text(json.dumps(journal));os.replace(temp,JOURNAL)
def timestamp(value):
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    if date.tzinfo is None: raise ValueError('Attempt timestamp has no timezone.')
    return int(date.timestamp()*1000)
def card_reviews(cid):
    return bridge.call('getReviewsOfCards',cards=[cid]).get(str(cid),[])
def sync(data,index,profile,card_id=None):
    journal=load()
    if profile!=journal['profile']: raise RuntimeError('Review sync paused: open Anki profile '+journal['profile']+'.')
    records=journal.setdefault('records',{});scored={a['id']:a for a in data['attempts'] if isinstance(a.get('is_correct'),bool)}
    cards={c['id']:c for c in data['cards']};historical=[];future=[];skipped=0
    for attempt in sorted(scored.values(),key=lambda a:a['answered_at']):
        if card_id and attempt['card_id']!=card_id: continue
        entry=records.get(attempt['id'])
        if entry and entry.get('state')=='done': continue
        card=cards.get(attempt['card_id']);note=bridge.match_card(card,index) if card else None
        if not note or len(note.get('cards',[]))!=1: skipped+=1;continue
        cid=note['cards'][0];ease=3 if attempt['is_correct'] else 1
        if timestamp(attempt['answered_at'])<journal['enabled_at_ms']:
            historical.append((attempt,cid,ease))
        else:future.append((attempt,cid,ease))
    imported=recorded=uncertain=0
    if historical:
        # Account for all existing collection-wide review IDs, which are unique globally.
        all_cids=sorted({cid for n in bridge.CACHE['notes'] for cid in n.get('cards',[])})
        existing={};used=set()
        for i in range(0,len(all_cids),500):
            result=bridge.call('getReviewsOfCards',cards=all_cids[i:i+500])
            for cid,rows in result.items():
                for r in rows:existing[r['id']]=(int(cid),r);used.add(r['id'])
        for entry in records.values():
            if 'row' in entry:used.add(entry['row'][0])
        rows=[];pending=[]
        for attempt,cid,ease in historical:
            entry=records.get(attempt['id'])
            if entry and entry.get('row'):
                row=entry['row'];found=existing.get(row[0])
                if found:
                    if found[0]!=cid or found[1]['ease']!=ease: raise RuntimeError('Review ID conflict; import paused.')
                    entry['state']='done';save(journal);continue
            else:
                original=timestamp(attempt['answered_at']);rid=original
                while rid in used:rid+=1
                used.add(rid)
                # Filtered/non-rescheduling practice review; no invented duration or interval.
                row=[rid,cid,-1,ease,0,0,0,0,3]
                records[attempt['id']]={'state':'pending','mode':'history','row':row}
            rows.append(row);pending.append(attempt['id'])
        save(journal)
        for i in range(0,len(rows),100):
            batch=rows[i:i+100];ids=pending[i:i+100]
            bridge.call('insertReviews',reviews=batch)
            verified=bridge.call('getReviewsOfCards',cards=sorted({r[1] for r in batch}))
            for aid,row in zip(ids,batch):
                match=next((r for r in verified.get(str(row[1]),[]) if r['id']==row[0] and r['ease']==row[3]),None)
                if not match:raise RuntimeError('Could not verify imported review; retry Sync Anki.')
                records[aid]['state']='done';imported+=1
            save(journal)
    for attempt,cid,ease in future:
        aid=attempt['id'];entry=records.get(aid);reviews=card_reviews(cid)
        if entry and entry.get('state')=='pending':
            added=[r for r in reviews if r['id'] not in entry['before'] and r['id']>=entry['started_ms'] and r['ease']==ease]
            if len(added)==1:
                entry.update(state='done',review_id=added[0]['id']);save(journal);recorded+=1
            else:uncertain+=1
            # Never repeat an ambiguous scheduler action automatically.
            continue
        records[aid]={'state':'pending','mode':'scheduler','cid':cid,'ease':ease,'started_ms':int(time.time()*1000),'before':[r['id'] for r in reviews]}
        save(journal)
        result=bridge.call('answerCards',answers=[{'cardId':cid,'ease':ease}])
        if result!=[True]:
            records[aid]['state']='rejected';save(journal);skipped+=1;continue
        after=card_reviews(cid);added=[r for r in after if r['id'] not in records[aid]['before'] and r['ease']==ease]
        if len(added)==1:
            records[aid].update(state='done',review_id=added[0]['id']);save(journal);recorded+=1
        else:uncertain+=1
    return {'history_imported':imported,'reviews_recorded':recorded,'reviews_synced_total':sum(r.get('state')=='done' for r in records.values()),'reviews_skipped':skipped,'reviews_uncertain':uncertain}
