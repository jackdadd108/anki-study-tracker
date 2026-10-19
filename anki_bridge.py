"""Local AnkiConnect tagging bridge. Does not submit Anki reviews."""
import json,re,html,time,threading
from collections import defaultdict
from urllib.request import Request,build_opener,ProxyHandler
SYNC_LOCK=threading.Lock()
CACHE={'time':0,'profile':None,'notes':[]}

def call(action,**params):
    raw=json.dumps({'action':action,'version':6,'params':params}).encode()
    req=Request('http://127.0.0.1:8766',data=raw,headers={'Content-Type':'application/json'})
    try:
        with build_opener(ProxyHandler({})).open(req,timeout=15) as response: result=json.load(response)
    except Exception as e: raise RuntimeError('Open Anki Desktop with AnkiConnect on port 8766, then try Sync Anki again.') from e
    if result.get('error'): raise RuntimeError('Anki: '+str(result['error']))
    return result['result']

def plain(value):
    value=re.sub(r'<(?:br\s*/?|/div|/p)>','\n',str(value),flags=re.I)
    return html.unescape(re.sub(r'<[^>]*>','',value)).strip()

def norm(value): return re.sub(r'\s+',' ',plain(value)).strip().casefold()
def identity(question,options=None,chapter='',number=''):
    parts=re.split(r'(?:^|\n)\s*([a-e])[.)]\s+',plain(question),flags=re.I)
    embedded=[parts[i+1].strip() for i in range(1,len(parts)-1,2)]
    if len(embedded)>=2: question=parts[0];options=embedded
    clean_options=[re.sub(r'^\s*[a-e][.)]\s+','',plain(o),flags=re.I) for o in (options or [])]
    return (norm(question),tuple(norm(o) for o in clean_options),norm(chapter),norm(number))

def note_identity(note):
    fields={k.lower().replace(' ','').replace('_',''):v['value'] for k,v in note['fields'].items()}
    question=fields.get('question') or fields.get('front') or next(iter(fields.values()),'')
    options=plain(fields.get('options',''))
    parts=re.split(r'(?:^|\n)\s*([a-e])[.)]\s+',options,flags=re.I)
    opts=[parts[i+1].strip() for i in range(1,len(parts)-1,2)]
    return identity(question,opts,fields.get('chapter',''),fields.get('questionnumber',''))

def card_identity(card):
    source=card.get('source_fields',{})
    return identity(card['question'],card.get('options',[]),card.get('chapter') or source.get('chapter',''),card.get('question_number') or source.get('questionnumber',''))

def index_notes(notes):
    strict=defaultdict(list);basic=defaultdict(list);fronts=defaultdict(list);backs=defaultdict(list)
    for n in notes:
        key=note_identity(n);strict[key].append(n);basic[key[:2]].append(n)
        fields={k.casefold():v['value'] for k,v in n['fields'].items()}
        front=fields.get('front') or fields.get('question','');back=fields.get('back') or fields.get('answer','')
        fronts[norm(front)].append(n)
        if back: backs[norm(back)].append(n)
    return strict,basic,fronts,backs,{n['noteId']:n for n in notes}

def match_card(card,index):
    link=card.get('anki_note_link',{})
    if link.get('profile')==CACHE.get('profile') and len(index)>4 and link.get('note_id') in index[4]: return index[4][link['note_id']]
    if card.get('anki_match_original'): card=card['anki_match_original']
    strict,basic,fronts,backs=index[:4];key=card_identity(card);matches=strict.get(key,[])
    if not matches and not any(key[2:]): matches=basic.get(key[:2],[])
    if not matches:
        # Older tracker imports split unlettered options into an array.
        matches=fronts.get(norm(card['question']+' '+' '.join(card.get('options',[]))),[])
    if not matches and card.get('answer'):
        # Require an exact explanation match and the question stem, never fuzzy similarity.
        matches=[n for n in backs.get(norm(card['answer']),[]) if key[0] in note_identity(n)[0]]
    return matches[0] if len(matches)==1 else None

def stats_by_card(data):
    events={}
    for e in data['attempts']+data.get('daily_completions',[]): events[e['id']]=e
    groups=defaultdict(list)
    for e in events.values(): groups[(e['deck_id'],e['card_id'])].append(e)
    result={}
    for key,rows in groups.items():
        scored=sorted([r for r in rows if isinstance(r.get('is_correct'),bool)],key=lambda r:r['answered_at'])
        result[key]={'attempts':len(rows),'correct':sum(r['is_correct'] for r in scored),'wrong':sum(not r['is_correct'] for r in scored),'latest_wrong':bool(scored and not scored[-1]['is_correct'])}
    return result

def desired_tags(counts):
    tags={'tracker::attempted',f"tracker::attempts::{counts['attempts']}",f"tracker::correct::{counts['correct']}",f"tracker::incorrect::{counts['wrong']}"}
    if counts['latest_wrong']: tags.add('tracker::wrong')
    return tags

def sync(data,card_id=None,refresh=False):
    call('version');profile=call('getActiveProfile')
    if refresh or CACHE['profile']!=profile or time.time()-CACHE['time']>300:
        ids=call('findNotes',query='');notes=[]
        for i in range(0,len(ids),500):notes.extend(call('notesInfo',notes=ids[i:i+500]))
        CACHE.update(time=time.time(),profile=profile,notes=notes)
    index=index_notes(CACHE['notes']);counts=stats_by_card(data);matched=unmatched=updated=0;used={};plans=[]
    for card in data['cards']:
        key=(card['deck_id'],card['id'])
        if key not in counts or card_id and card['id']!=card_id: continue
        note=match_card(card,index)
        if not note: unmatched+=1;continue
        # Two tracker cards must never silently overwrite the same Anki note's counters.
        if note['noteId'] in used: unmatched+=1;continue
        used[note['noteId']]=key;matched+=1;plans.append((note,counts[key]))
    for note,count in plans:
        existing=set(note['tags']);desired=desired_tags(count)
        owned={t for t in existing if t in ('tracker::attempted','tracker::wrong') or re.fullmatch(r'tracker::(?:attempts|correct|incorrect)::\d+',t)}
        remove=owned-desired;add=desired-existing
        if remove:call('removeTags',notes=[note['noteId']],tags=' '.join(sorted(remove)))
        if add:call('addTags',notes=[note['noteId']],tags=' '.join(sorted(add)))
        note['tags']=sorted((existing-remove)|add);updated+=bool(remove or add)
    return {'connected':True,'profile':profile,'matched':matched,'unmatched':unmatched,'updated':updated,'synced_at':time.time()}
