#!/usr/bin/env python3
import json, os, sqlite3, tempfile, zipfile, re, html, uuid, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
ROOT = Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(ROOT))
import anki_bridge
import answers
LOCK = threading.Lock()
def clean(s):
    s = re.sub(r'<(?:br\s*/?|/p|/div)>', '\n', s, flags=re.I)
    return html.unescape(re.sub('<[^>]+>', '', s)).strip()
def extract_images(raw):
    import hashlib
    from html.parser import HTMLParser
    from urllib.parse import unquote
    class Images(HTMLParser):
        def __init__(self): super().__init__(); self.names=[]
        def handle_starttag(self, tag, attrs):
            if tag.lower()=='img':
                src=dict(attrs).get('src','')
                if src: self.names.append(unquote(src))
    media_dir=ROOT/'static'/'media'; media_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(__import__('io').BytesIO(raw)) as z:
        mapping=json.loads(z.read('media')) if 'media' in z.namelist() else {}
        lookup={name:key for key,name in mapping.items()}
        cache={}
        def images(markup):
            parser=Images();parser.feed(markup);result=[]
            for name in parser.names:
                if name not in lookup: continue
                if name not in cache:
                    info=z.getinfo(lookup[name])
                    if info.file_size>20_000_000: continue
                    content=z.read(lookup[name])
                    ext='.png' if content.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if content.startswith(b'\xff\xd8\xff') else '.gif' if content.startswith((b'GIF87a',b'GIF89a')) else '.webp' if content.startswith(b'RIFF') and content[8:12]==b'WEBP' else None
                    if not ext: continue
                    filename=hashlib.sha256(content).hexdigest()+ext
                    path=media_dir/filename
                    if not path.exists(): path.write_bytes(content)
                    cache[name]='/media/'+filename
                if cache.get(name) and cache[name] not in result: result.append(cache[name])
            return result
        dbname=next(n for n in ('collection.anki21','collection.anki2') if n in z.namelist())
        with tempfile.NamedTemporaryFile() as f:
            f.write(z.read(dbname));f.flush();conn=sqlite3.connect(f.name)
            try:
                models=json.loads(conn.execute('SELECT models FROM col').fetchone()[0])
                rows=conn.execute('SELECT mid,flds FROM notes ORDER BY id').fetchall()
            finally: conn.close()
        results=[]
        for mid,flds in rows:
            fields=flds.split('\x1f');names=[f['name'].lower().replace(' ','').replace('_','') for f in models.get(str(mid),{}).get('flds',[])];named=dict(zip(names,fields))
            front=named.get('question') or named.get('front') or fields[0]
            back=named.get('answer') or named.get('back') or (fields[1] if len(fields)>1 else '')
            results.append(dict(question_images=images(front+' '+named.get('questionimage','')),answer_images=images(back+' '+named.get('explanation','')+' '+named.get('answerimage',''))))
        return results
def import_apkg(raw, name):
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(__import__('io').BytesIO(raw)) as z:
            candidates = [n for n in z.namelist() if n in ('collection.anki2','collection.anki21')]
            if not candidates: raise ValueError('This deck uses the newer compressed Anki format. Export with “Support older Anki versions” enabled, then try again.')
            info=z.getinfo(candidates[0])
            if info.file_size > 250_000_000: raise ValueError('Deck database is too large (maximum 250 MB).')
            db=Path(temp)/'collection.db'; db.write_bytes(z.read(candidates[0]))
        conn=sqlite3.connect(db)
        try:
            notes=conn.execute('SELECT mid, flds FROM notes ORDER BY id').fetchall()
            models=json.loads(conn.execute('SELECT models FROM col').fetchone()[0])
        finally: conn.close()
    media=extract_images(raw)
    did=str(uuid.uuid4()); cards=[]
    for note_index, (mid, flds) in enumerate(notes):
        fields=[clean(s) for s in flds.split('\x1f')]
        names=[f['name'].lower().replace(' ', '').replace('_','') for f in models.get(str(mid),{}).get('flds',[])]
        named=dict(zip(names,fields))
        if len(fields)<2: continue
        front=named.get('question') or named.get('front') or fields[0]
        back=named.get('answer') or named.get('back') or fields[1]
        explanation=named.get('explanation','')
        if explanation: back += '\n\n'+explanation
        if not front: continue
        option_text=named.get('options','')
        parts=re.split(r'(?:^|\n)\s*([A-Ea-e])[.)]\s+', option_text or front)
        options=[parts[i+1].strip() for i in range(1,len(parts)-1,2)]
        if not options:
            options=[named[k] for k in ('optiona','optionb','optionc','optiond','optione') if named.get(k)]
        match=re.match(r'^\s*([A-Ea-e])[.)\s]',back)
        cards.append(dict(id=str(uuid.uuid4()),deck_id=did,question=front if option_text else parts[0].strip(),answer=back,options=options,correct_option=match.group(1).upper() if match else '',chapter=named.get('chapter',''),question_number=named.get('questionnumber',''),source_fields=named,**media[note_index]))
    if not cards: raise ValueError('No front/back cards found in this deck.')
    return dict(id=did,name=name,card_count=len(cards),current_index=0),cards
def record_completion(data, event):
    from datetime import datetime, timezone
    token=event.get('id')
    if not isinstance(token,str) or not token: raise ValueError('Missing attempt ID.')
    if any(a['id']==token for a in data['attempts']+data.get('daily_completions',[])): return data
    deck=next((d for d in data['decks'] if d['id']==event.get('deck_id')),None)
    card=next((c for c in data['cards'] if c['id']==event.get('card_id') and c['deck_id']==event.get('deck_id')),None)
    if not deck or not card: raise ValueError('Deck or card not found.')
    correct=event.get('correct_options',event.get('correct_option'))
    correct_set=answers.normalize(correct) if correct is not None else []
    selected_set=answers.normalize(event.get('selected_options',event.get('selected_option')))
    if correct is not None and (not correct_set or len(selected_set)!=1): raise ValueError('Select an answer and confirm the correct answer(s).')
    history=data['attempts']+data.get('daily_completions',[])
    kind='revision' if any(a['card_id']==card['id'] and a['deck_id']==deck['id'] for a in history) else 'new'
    saved=dict(id=token,deck_id=deck['id'],card_id=card['id'],answered_at=datetime.now(timezone.utc).isoformat(),study_kind=kind)
    if correct is None:
        data.setdefault('daily_completions',[]).append(saved)
    else:
        saved.update(selected_option=','.join(selected_set),selected_options=selected_set,correct_options=correct_set,is_correct=answers.grade(selected_set,correct_set))
        data['attempts'].append(saved);card['correct_option']=','.join(correct_set);card['correct_options']=correct_set
    index=event.get('current_index')
    if index is not None:
        if not isinstance(index,int) or index<0: raise ValueError('Invalid progress index.')
        deck['current_index']=index
    return data
def edit_card(data,event):
    from datetime import datetime,timezone
    card=next((c for c in data['cards'] if c['id']==event.get('id')),None)
    if not card: raise ValueError('Card not found.')
    question=event.get('question');answer=event.get('answer');options=event.get('options');correct=event.get('correct_option','')
    if not isinstance(question,str) or not question.strip() or len(question)>50000: raise ValueError('Enter a question (maximum 50,000 characters).')
    if not isinstance(answer,str) or not answer.strip() or len(answer)>100000: raise ValueError('Enter an answer or explanation.')
    if not isinstance(options,list) or len(options)>26 or any(not isinstance(o,str) or not o.strip() or len(o)>20000 for o in options): raise ValueError('Enter up to 26 nonempty options.')
    if correct and correct not in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'[:len(options)]): raise ValueError('Correct letter must match one of the options.')
    keys=('question','answer','options','correct_option','chapter','question_number','source_fields')
    if 'anki_match_original' not in card: card['anki_match_original']={k:card[k] for k in keys if k in card}
    card.update(question=question.strip(),answer=answer.strip(),options=[o.strip() for o in options],correct_option=correct,edited_correct_option=True,edited_at=datetime.now(timezone.utc).isoformat())
    return data
SPEECH_LOCK=threading.Lock()
SPEECH_PROCESS=None
SPEECH_ID=None
def speech_voices():
    import subprocess
    result=subprocess.run(['/usr/bin/say','-v','?'],capture_output=True,text=True,check=True)
    voices=[]
    for line in result.stdout.splitlines():
        match=re.match(r'^(.*?)\s+(en_[A-Z]+)\s+#',line)
        if match and match.group(1).strip() not in voices: voices.append(match.group(1).strip())
    return voices

def stop_speech():
    global SPEECH_PROCESS,SPEECH_ID
    with SPEECH_LOCK:
        if SPEECH_PROCESS and SPEECH_PROCESS.poll() is None: SPEECH_PROCESS.terminate()
        SPEECH_PROCESS=None;SPEECH_ID=None

def start_speech(text,voice,rate):
    import subprocess
    global SPEECH_PROCESS,SPEECH_ID
    voices=speech_voices()
    voice=voice or ('Ava (Premium)' if 'Ava (Premium)' in voices else voices[0])
    if voice not in voices: raise ValueError('Voice is not installed on this Mac.')
    if rate not in (1,1.1,1.2): raise ValueError('Invalid reading speed.')
    if not isinstance(text,str) or not text.strip() or len(text)>100000: raise ValueError('Invalid answer text.')
    stop_speech()
    with SPEECH_LOCK:
        process=subprocess.Popen(['/usr/bin/say','-v',voice,'-r',str(round(180*rate))],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        SPEECH_PROCESS=process;SPEECH_ID=str(uuid.uuid4());speech_id=SPEECH_ID
        threading.Thread(target=lambda:process.communicate(text.encode()),daemon=True).start()
    return {'id':speech_id,'voice':voice}
def sync_anki(card_id=None,refresh=False):
    with anki_bridge.SYNC_LOCK:
        with LOCK: data=json.loads((ROOT/'data.json').read_text())
        try:
            result=anki_bridge.sync(data,card_id,refresh)
            import review_sync
            if review_sync.JOURNAL.exists(): result.update(review_sync.sync(data,anki_bridge.index_notes(anki_bridge.CACHE['notes']),result['profile'],card_id))
        except Exception as e: result={'connected':False,'error':str(e)}
        with LOCK:
            data=json.loads((ROOT/'data.json').read_text());data['anki_sync']=result
            tmp=ROOT/'data.tmp';tmp.write_text(json.dumps(data));os.replace(tmp,ROOT/'data.json')
        return result
def open_anki_note(card_id):
    with anki_bridge.SYNC_LOCK:
        with LOCK:
            data=json.loads((ROOT/'data.json').read_text())
            card=next((c for c in data['cards'] if c['id']==card_id),None)
        if not card: raise ValueError('Card not found.')
        profile=anki_bridge.call('getActiveProfile')
        import time
        for refresh in (False,True):
            if refresh or anki_bridge.CACHE['profile']!=profile or time.time()-anki_bridge.CACHE['time']>300:
                ids=anki_bridge.call('findNotes',query='');notes=[]
                for i in range(0,len(ids),500):notes.extend(anki_bridge.call('notesInfo',notes=ids[i:i+500]))
                anki_bridge.CACHE.update(time=time.time(),profile=profile,notes=notes)
            note=anki_bridge.match_card(card,anki_bridge.index_notes(anki_bridge.CACHE['notes']))
            if note: break
        if not note: raise ValueError('No unique matching Anki note found for this question.')
        live=anki_bridge.call('notesInfo',notes=[note['noteId']])
        if not live or not live[0].get('noteId'): raise ValueError('The matching Anki note no longer exists.')
        linked_cards=anki_bridge.call('guiBrowse',query='nid:'+str(note['noteId']))
        if not linked_cards: raise ValueError('No Anki cards found for this note.')
        anki_bridge.call('guiSelectCard',card=linked_cards[0])
        with LOCK:
            data=json.loads((ROOT/'data.json').read_text())
            current=next(c for c in data['cards'] if c['id']==card_id)
            current['anki_note_link']={'profile':profile,'note_id':note['noteId']}
            temp=ROOT/'data.tmp';temp.write_text(json.dumps(data));os.replace(temp,ROOT/'data.json')
        return {'opened':True,'note_id':note['noteId']}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'static'),**kw)
    def send_json(self,obj,status=200):
        raw=json.dumps(obj).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/health': return self.send_json({'app':'anki-study-tracker','ready':True})
        if self.path=='/api/anki/status':
            with LOCK: return self.send_json(json.loads((ROOT/'data.json').read_text()).get('anki_sync',{}))
        if self.path=='/api/speech/voices': return self.send_json({'voices':speech_voices()})
        if self.path=='/api/speech/status':
            with SPEECH_LOCK: return self.send_json({'id':SPEECH_ID,'speaking':bool(SPEECH_PROCESS and SPEECH_PROCESS.poll() is None)})
        if self.path=='/api/data':
            with LOCK: self.send_json(json.loads((ROOT/'data.json').read_text()))
        else: super().do_GET()
    def do_POST(self):
        if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'): return self.send_json({'error':'Origin rejected'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>100_000_000: raise ValueError('Upload too large (maximum 100 MB).')
            raw=self.rfile.read(size)
            if self.path=='/api/anki/open': return self.send_json(open_anki_note(json.loads(raw).get('card_id')))
            if self.path=='/api/anki/sync': return self.send_json(sync_anki(refresh=True))
            if self.path=='/api/speech/stop':
                stop_speech();return self.send_json({'stopped':True})
            if self.path=='/api/speech/start':
                event=json.loads(raw);return self.send_json(start_speech(event.get('text'),event.get('voice'),event.get('rate',1)))
            with LOCK:
                data=json.loads((ROOT/'data.json').read_text())
                if self.path=='/api/import':
                    deck,cards=import_apkg(raw,__import__('urllib.parse',fromlist=['unquote']).unquote(self.headers.get('X-Deck-Name','Imported deck')))
                    data['decks'].append(deck); data['cards'].extend(cards)
                elif self.path=='/api/complete':
                    data=record_completion(data,json.loads(raw))
                elif self.path=='/api/card/edit':
                    data=edit_card(data,json.loads(raw))
                elif self.path=='/api/save':
                    incoming=json.loads(raw)
                    if not all(isinstance(incoming.get(k),list) for k in ('decks','cards','attempts')): raise ValueError('Invalid backup format.')
                    data=incoming
                else: return self.send_json({'error':'Not found'},404)
                tmp=ROOT/'data.tmp'; tmp.write_text(json.dumps(data)); os.replace(tmp,ROOT/'data.json')
            self.send_json(data)
            if self.path=='/api/complete': threading.Thread(target=sync_anki,args=(json.loads(raw)['card_id'],),daemon=True).start()
        except Exception as e: self.send_json({'error':str(e)},400)
if __name__=='__main__':
    print('Anki Study Tracker: http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
