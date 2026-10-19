const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, period=30, active=null, queue=[], pos=0, selected='', revealed=false, retryMode=false, saving=false, attemptToken=null, dailyExpanded=false;
const day=d=>{const x=new Date(d);return `${x.getFullYear()}-${String(x.getMonth()+1).padStart(2,'0')}-${String(x.getDate()).padStart(2,'0')}`}, today=()=>day(new Date());
const cardsFor=id=>data.cards.filter(c=>c.deck_id===id), attemptsFor=id=>data.attempts.filter(a=>a.deck_id===id), latest=()=>{const m=new Map();[...data.attempts].sort((a,b)=>a.answered_at.localeCompare(b.answered_at)).forEach(a=>m.set(a.card_id,a));return m}, wrong=id=>{const m=latest();return cardsFor(id).filter(c=>m.has(c.id)&&!m.get(c.id).is_correct)}, accuracy=a=>a.length?Math.round(a.filter(x=>x.is_correct).length/a.length*100)+'%':'—';
function notify(s){$('#notice').textContent=s;$('#notice').hidden=false;setTimeout(()=>$('#notice').hidden=true,5000)}
async function request(url,opts){const r=await fetch(url,opts);const j=await r.json();if(!r.ok)throw Error(j.error||'Request failed');return j}
async function persist(){await request('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})}
function confirmAction(title,text,fn){$('#confirm-title').textContent=title;$('#confirm-text').textContent=text;$('#confirm').showModal();$('#confirm-ok').onclick=async()=>{$('#confirm').close();try{await fn()}catch(e){notify(e.message)}}}
$('#cancel').onclick=()=>$('#confirm').close();
function render(){stopReading();active=null;$('#study-toolbar').hidden=true;$('#daily-progress').hidden=true;$('#study').hidden=true;$('#dashboard').hidden=false;$('#crumb').textContent='Overview';$('#home').classList.add('active');$('#side-decks').innerHTML=data.decks.map(d=>`<button class="nav" data-open="${esc(d.id)}">▤ &nbsp; ${esc(d.name)}</button>`).join('');
const dates=Array.from({length:period},(_,i)=>{const d=new Date();d.setDate(d.getDate()-period+1+i);return day(d)}), counts=dates.map(d=>data.attempts.filter(a=>day(a.answered_at)===d).length), max=Math.max(1,...counts), todays=data.attempts.filter(a=>day(a.answered_at)===today());
const overallScore=ExamScoring.calculate(data.attempts);
$('#dashboard').innerHTML=`<div class="heading-row"><div><div class="eyebrow">A LITTLE PROGRESS, EVERY DAY</div><h1>Practice. Know your score.</h1><p>Your decks, your progress. Build knowledge that stays with you.</p></div><button class="primary" id="import">＋ Import deck</button></div><div class="stats"><div class="stat"><small>Cards reviewed today</small><strong class="accent">${todays.length}</strong><span class="hint">Every review counts</span></div><div class="stat"><small>Overall exam score</small><strong>${overallScore.attempted?(overallScore.exam/overallScore.attempted*100).toFixed(1)+'%':'—'}</strong><span class="hint">${Number(overallScore.exam.toFixed(2))} / ${overallScore.attempted.toLocaleString()} marks · +1 correct, −0.25 wrong</span></div><div class="stat"><small>Cards in your library</small><strong>${data.cards.length.toLocaleString()}</strong><span class="hint">${data.decks.length} decks to explore</span></div></div><div class="panel"><div class="row"><h2>Study activity</h2><div class="periods">${[7,30,90].map(n=>`<button data-period="${n}" class="${n===period?'selected':''}">${n} days</button>`).join('')}</div></div><div class="chart">${counts.map((n,i)=>`<button class="bar" style="height:${Math.max(4,n/max*100)}%" title="${dates[i]}: ${n} reviews" aria-label="${dates[i]}: ${n} reviews" data-day="${i}"></button>`).join('')}</div><div class="chart-labels"><span>${dates[0]}</span><span id="chart-detail">Saved answers, including retries</span><span>Today</span></div></div><div class="section-title"><h2>Your decks <span> / ${data.decks.length}</span></h2><span>Pick up where you left off</span></div><div class="deck-grid">${data.decks.map(d=>{const cs=cardsFor(d.id),idx=Math.min(d.current_index||0,cs.length),at=attemptsFor(d.id);return `<article class="deck"><div class="deck-icon">▤</div><div class="mini-actions"><button data-redo="${esc(d.id)}">↺ Restart</button><button aria-label="Delete ${esc(d.name)}" data-delete="${esc(d.id)}">×</button></div><h3>${esc(d.name.replaceAll('_',' '))}</h3><p>${cs.length.toLocaleString()} cards · ${accuracy(at)} accuracy</p><div class="progress"><i style="width:${cs.length?idx/cs.length*100:0}%"></i></div><div class="deck-bottom"><small>${idx} / ${cs.length} completed</small><button data-open="${esc(d.id)}">${idx===cs.length?'Review again':'Continue studying'} →</button></div></article>`}).join('')||'<div class="empty">Import your first .apkg deck to begin.</div>'}</div><div class="section-title"><h2>Another chance to learn</h2><span>Wrong answers · practise until correct</span></div><div class="panel">${data.decks.map(d=>{const n=wrong(d.id).length;return `<div class="retry"><div><h3>${esc(d.name.replaceAll('_',' '))}</h3><small>${n?`${n} cards ready for another try`:'All caught up. Nice work.'}</small></div><div><button data-export="${esc(d.id)}" ${n?'':'disabled'}>↓ Export CSV</button> <button data-retry="${esc(d.id)}" ${n?'':'disabled'}>Practise ${n} cards →</button></div></div>`}).join('')||'<div class="empty">Your retry cards will appear here.</div>'}</div>`;
$('#import').onclick=()=>$('#upload').click();document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openDeck(b.dataset.open));document.querySelectorAll('[data-period]').forEach(b=>b.onclick=()=>{period=Number(b.dataset.period);render()});document.querySelectorAll('[data-day]').forEach(b=>b.onclick=()=>$('#chart-detail').textContent=`${dates[b.dataset.day]} · ${counts[b.dataset.day]} reviews`);document.querySelectorAll('[data-retry]').forEach(b=>b.onclick=()=>openDeck(b.dataset.retry,true));document.querySelectorAll('[data-redo]').forEach(b=>b.onclick=()=>confirmAction('Restart this deck?','Your past answers and accuracy history will be kept.',async()=>{data.decks.find(d=>d.id===b.dataset.redo).current_index=0;await persist();openDeck(b.dataset.redo)}));document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>confirmAction('Remove this deck?','The deck and its answers will be removed locally. Download a backup first if you want to restore them.',async()=>{const id=b.dataset.delete;data.decks=data.decks.filter(d=>d.id!==id);data.cards=data.cards.filter(c=>c.deck_id!==id);data.attempts=data.attempts.filter(a=>a.deck_id!==id);await persist();render()}));document.querySelectorAll('[data-export]').forEach(b=>b.onclick=()=>{const quote=s=>'"'+String(s??'').replaceAll('"','""')+'"';const rows=wrong(b.dataset.export).map(c=>[c.question,c.options?.join('\n'),c.answer]);download('wrong-answers.csv','\ufeff'+[['Question','Options','Answer'],...rows].map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv')})}
function openDeck(id,retry=false){active=data.decks.find(d=>d.id===id);retryMode=retry;queue=retry?wrong(id):cardsFor(id);pos=retry?0:Math.min(active.current_index||0,queue.length);selected='';revealed=false;attemptToken=crypto.randomUUID();$('#daily-progress').hidden=false;updateDaily();$('#dashboard').hidden=true;$('#study').hidden=false;$('#home').classList.remove('active');$('#crumb').textContent=active.name;renderCard()}

function cardContent(c){
 const parts=c.question.split(/(?:^|\n)\s*([A-Ea-e])[.)]\s+/);
 const embedded=[];
 for(let i=1;i<parts.length-1;i+=2)embedded.push(parts[i+1].trim());
 const stored=c.options||[],labelled=stored.length>1&&stored.every((o,i)=>new RegExp('^\\s*'+String.fromCharCode(65+i)+'[.)]\\s+','i').test(o));
 const options=embedded.length>=2?embedded:labelled?stored.map((o,i)=>o.replace(new RegExp('^\\s*'+String.fromCharCode(65+i)+'[.)]\\s+','i'),'')):stored;
 const question=embedded.length>=2?parts[0].trim():c.question;
 const first=c.answer.split(/\n/)[0].trim().toLowerCase().replace(/[.\s]+$/,'');
 const idx=options.findIndex(o=>o.toLowerCase().replace(/[.\s]+$/,'')===first);
 return {question,options,inferred:idx>=0?String.fromCharCode(65+idx):''};
}
function cardImages(urls,label){return (urls||[]).filter(url=>/^\/media\/[a-f0-9]{64}\.(png|jpg|gif|webp)$/.test(url)).map((url,i)=>`<figure class="anki-image"><a href="${esc(url)}" target="_blank" rel="noopener" title="Open full-size image"><img src="${esc(url)}" alt="${label} image ${i+1}" loading="lazy"></a><figcaption>Click image to view full size</figcaption></figure>`).join('')}
function updateStudyToolbar(){
 const score=ExamScoring.calculate(attemptsFor(active.id));
 $('#study-toolbar').hidden=false;
 $('#study-toolbar').innerHTML=`<button class="quiet" id="back">← All decks</button><div class="study-score"><span>Score <strong>${score.percent===null?'—':score.percent.toFixed(1)+'%'}</strong></span><small>${score.correct} correct / ${score.attempted} attempted · this deck</small></div><div class="study-score"><span>Exam score <strong>${Number(score.exam.toFixed(2))} / ${score.attempted}</strong></span><small>Correct +1 · Wrong −0.25</small></div>`;
 $('#back').onclick=render;
}
function renderCard(){
 stopReading();updateStudyToolbar();updateDaily();
 if(pos>=queue.length){$('#study').innerHTML=`<div class="panel"><div class="eyebrow">SESSION COMPLETE</div><h1>A little more knowledge, earned.</h1><p>Your answers are saved.</p><button class="primary" id="done">Back to overview →</button></div>`;$('#done').onclick=render;return}
 const c=queue[pos],content=cardContent(c),opts=content.options.length?content.options:['A','B','C','D','E'],correct=AnswerKey.resolve(c,opts),multiple=correct.length>1,chosen=AnswerKey.normalize(selected);
 const feedback=(letter)=>!revealed||!correct.length?'':correct.includes(letter)?'option-correct':chosen.includes(letter)?'option-wrong':'';
 $('#study').innerHTML=`<div class="section-title"><div><div class="eyebrow">${retryMode?'RETRY SESSION':'STUDY SESSION'}</div><h1>${esc(active.name.replaceAll('_',' '))}</h1></div><div class="question-navigation"><button id="previous-question" ${pos===0?'disabled':''}>← Previous</button><span>${pos+1} / ${queue.length} · ${Math.max(0,queue.length-pos-1)} left</span><button id="next-question" ${pos>=queue.length-1?'disabled':''}>Next →</button></div></div><div class="progress"><i style="width:${pos/queue.length*100}%"></i></div><div class="panel"><div class="question-card-heading"><div class="eyebrow">QUESTION ${pos+1}</div><button id="edit-question" class="quiet" title="Open this note in Anki (E)" aria-keyshortcuts="e">↗ Edit in Anki (E)</button></div><div class="question">${esc(content.question)}</div>${cardImages(c.question_images,'Question')}<div role="group" aria-label="Answer options">${opts.map((option,i)=>{const letter=String.fromCharCode(65+i);return `<label class="option ${chosen.includes(letter)?'chosen':''} ${feedback(letter)}"><input type="radio" name="answer-option" data-option="${letter}" value="${letter}" ${chosen.includes(letter)?'checked':''} ${revealed?'disabled':''}><b>${letter}</b><span>${esc(option)}</span></label>`}).join('')}</div>${revealed?`<p class="answer-result" role="status">${correct.length?`Correct ${multiple?'answers':'answer'}: <strong>${correct.join(', ')}</strong>. ${AnswerKey.grade(chosen,correct)?'Correct selection.':'Your selection was incorrect.'}`:'Confirm the correct answer below before saving.'}</p><div class="answer">${esc(c.answer)}${cardImages(c.answer_images,'Answer')}</div>${!correct.length?`<fieldset class="correct-choices"><legend>Confirm correct answer</legend><div>${opts.map((o,i)=>`<label><input type="radio" name="correct" value="${String.fromCharCode(65+i)}"><span>${String.fromCharCode(65+i)}</span></label>`).join('')}</div></fieldset>`:''}`:''}<div class="read-aloud-controls"><button id="read-aloud" class="primary" aria-keyshortcuts="r Shift+Space" ${revealed?'':'disabled'}>🔊 Read answer aloud (R)</button><label class="speech-speed">Speed <select id="speech-rate" aria-label="Reading speed">${[1,1.1,1.2].map(rate=>`<option value="${rate}" ${speechRate===rate?'selected':''}>${rate}×</option>`).join('')}</select></label><label class="speech-speed">Voice <select id="speech-voice" aria-label="Reading voice"><option value="">Best available Mac voice</option></select></label><button id="stop-reading" class="quiet" hidden>Stop reading</button><span id="speech-status" role="status"></span></div><div class="actions"><button id="mark-completed" class="quiet">Mark completed & next</button>${revealed?'<button class="primary" id="next" title="Save answer and next (Space)" aria-keyshortcuts="Space">Save answer & next → (Space)</button>':`<button class="primary" id="reveal" ${chosen.length?'':'disabled'}>Reveal answer</button>`}</div></div>`;
 $('#edit-question').onclick=()=>openInAnki(c);setupReadAloud(c,content,opts);$('#previous-question').onclick=()=>browseQuestion(-1);$('#next-question').onclick=()=>browseQuestion(1);
 document.querySelectorAll('[data-option]').forEach(input=>input.onchange=()=>{selected=input.value;revealed=true;renderCard()});
 $('#mark-completed').onclick=()=>completeCurrent(null,c);
 if(!revealed)$('#reveal').onclick=()=>{revealed=true;renderCard()};
 else $('#next').onclick=()=>{const key=correct.length?correct:Array.from(document.querySelectorAll('input[name=correct]:checked'),e=>e.value);if(!key.length)return notify('Confirm at least one correct answer.');completeCurrent(key.join(','),c)};
}
async function openInAnki(card){
 if(saving)return;stopReading();const button=$('#edit-question');button.disabled=true;button.textContent='Opening…';
 try{const result=await request('/api/anki/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({card_id:card.id})});notify('Opened this question in Anki’s editor.')}catch(err){notify(err.message)}finally{if($('#edit-question')){$('#edit-question').disabled=false;$('#edit-question').textContent='↗ Edit in Anki (E)'}}
}
let speechSession=0, speechRate=1, nativeSpeechId=null, speechBusy=false, macVoices=[], preferredVoice='';
try{const stored=Number(localStorage.getItem('anki-speech-rate'));if([1,1.1,1.2].includes(stored))speechRate=stored;preferredVoice=localStorage.getItem('anki-mac-voice')||'Ava (Premium)'}catch(e){}
function stopReading(){
 speechSession++;
 if(nativeSpeechId||speechBusy)fetch('/api/speech/stop',{method:'POST'}).catch(()=>{});
 nativeSpeechId=null;speechBusy=false;
 if($('#stop-reading'))$('#stop-reading').hidden=true;
 if($('#speech-status'))$('#speech-status').textContent='';
}
function populateVoices(){
 const select=$('#speech-voice');if(!select)return;
 select.innerHTML='<option value="">Best available Mac voice</option>'+macVoices.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
 select.value=preferredVoice;if(!select.value)select.value='';
}
async function loadMacVoices(){
 try{macVoices=(await request('/api/speech/voices')).voices;populateVoices()}catch(e){if($('#speech-status'))$('#speech-status').textContent='Restart the Anki app to enable Mac voices.'}
}
function setupReadAloud(card){
 const button=$('#read-aloud');button.title='Read or stop answer aloud (R or Shift + Space)';
 $('#speech-rate').onchange=e=>{speechRate=Number(e.target.value);try{localStorage.setItem('anki-speech-rate',String(speechRate))}catch(err){}};
 if(!revealed)$('#speech-status').textContent='Reveal the answer first. Shortcut: R or Shift + Space.';
 populateVoices();if(!macVoices.length)loadMacVoices();
 $('#speech-voice').onchange=e=>{preferredVoice=e.target.value;try{localStorage.setItem('anki-mac-voice',preferredVoice)}catch(err){}};
 button.onclick=async()=>{
  if(!revealed)return;
  if(nativeSpeechId||speechBusy){stopReading();return}
  const session=++speechSession;speechBusy=true;$('#stop-reading').hidden=false;$('#speech-status').textContent='Starting Mac voice…';
  try{
   const result=await request('/api/speech/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:card.answer,voice:preferredVoice,rate:speechRate})});
   if(session!==speechSession){fetch('/api/speech/stop',{method:'POST'}).catch(()=>{});return}
   nativeSpeechId=result.id;speechBusy=false;$('#speech-status').textContent=`Reading with ${result.voice} · R or Shift + Space to stop`;
  }catch(e){if(session===speechSession){nativeSpeechId=null;speechBusy=false;$('#stop-reading').hidden=true;$('#speech-status').textContent=e.message}}
 };
 $('#stop-reading').onclick=stopReading;
}
setInterval(async()=>{
 if(!nativeSpeechId)return;const id=nativeSpeechId;
 try{const status=await request('/api/speech/status');if(nativeSpeechId===id&&(!status.speaking||status.id!==id)){nativeSpeechId=null;if($('#stop-reading'))$('#stop-reading').hidden=true;if($('#speech-status'))$('#speech-status').textContent=''}}catch(e){}
},1000);
document.addEventListener('keydown',e=>{
 if(e.ctrlKey||e.altKey||e.metaKey||e.repeat||e.isComposing||!active||saving)return;
 if(e.target.closest('textarea,select,[contenteditable]:not([contenteditable="false"]),input:not([type="radio"]):not([type="checkbox"]):not([type="button"]):not([type="submit"])')||document.querySelector('dialog[open]'))return;
 const key=e.key.toLowerCase();
 const read=key==='r'||(e.code==='Space'&&e.shiftKey);
 const next=e.code==='Space'&&!e.shiftKey&&revealed;
 const button=key==='e'?$('#edit-question'):read&&revealed?$('#read-aloud'):next?$('#next'):null;
 if(!button||button.disabled)return;
 e.preventDefault();button.click();
});
function browseQuestion(direction){
 if(saving||pos+direction<0||pos+direction>=queue.length)return;
 pos+=direction;selected='';revealed=false;attemptToken=crypto.randomUUID();renderCard();
}
async function completeCurrent(correct,c){
 if(saving)return;
 const token=attemptToken,deck=active,index=pos,kind=DailyProgress.kind(data,c);
 saving=true;document.querySelectorAll('#next,#mark-completed,#back,#home,#side-decks button,#restore,#backup,#previous-question,#next-question').forEach(b=>b.disabled=true);
 try{
  const result=await request('/api/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:token,deck_id:deck.id,card_id:c.id,selected_option:selected,selected_options:AnswerKey.normalize(selected),correct_option:correct,correct_options:correct===null?null:AnswerKey.normalize(correct),study_kind:kind,current_index:retryMode?null:Math.max(deck.current_index||0,index+1),answered_at:new Date().toISOString()})});
  data=result;active=data.decks.find(d=>d.id===deck.id);queue=queue.map(card=>data.cards.find(c=>c.id===card.id)||card);pos=index+1;selected='';revealed=false;attemptToken=crypto.randomUUID();renderCard();
 }catch(e){notify('Progress could not be saved. Try again: '+e.message)}finally{saving=false;document.querySelectorAll('#next,#mark-completed,#back,#home,#side-decks button,#restore,#backup,#previous-question,#next-question').forEach(b=>b.disabled=false);if($('#previous-question'))$('#previous-question').disabled=pos===0;if($('#next-question'))$('#next-question').disabled=pos>=queue.length-1;updateDaily()}
}
async function saveMicroTarget(next){
 const old=data.micro_target;data.micro_target=next;saving=true;$('#micro-start').disabled=true;$('#micro-clear').disabled=true;
 try{await persist();notify(next?'Micro target started.':'Micro target cleared.')}catch(err){data.micro_target=old;notify(err.message)}finally{saving=false;$('#micro-start').disabled=false;$('#micro-clear').disabled=false;updateDaily()}
}
function updateMicroTarget(){
 const state=data.micro_target,summary=$('#micro-summary'),s=MicroTarget.stats(state,DailyProgress.events(data));
 summary.hidden=!s;$('#micro-clear').hidden=!s;$('#micro-start').textContent=s?'Start new target':'Start micro target';
 if(!s)return;
 $('#micro-status').textContent=s.reached?'Micro target reached ✓':s.expired?'Micro target · time up':'Micro target';
 $('#micro-count').textContent=`${s.completed} / ${state.target} done · ${s.remaining} left`;
 const seconds=Math.ceil(s.left/1000);$('#micro-clock').textContent=s.reached?'Completed':s.expired?'Start another when ready':`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')} remaining`;
 $('#micro-progress').value=s.percent;
}
function updateDaily(){
 if(!data||!active||$('#daily-progress').hidden)return;
 const s=DailyProgress.stats(data),hours=Math.floor(s.left/3600000),minutes=Math.floor(s.left/60000)%60;
 const schedule=s.remaining===0?'Daily target reached':s.overdue?'Deadline passed':Math.abs(s.delta)<1?'On schedule':`${Math.ceil(Math.abs(s.delta))} ${s.delta>=0?'ahead':'behind'} schedule`;
 const host=$('#daily-progress');
 if(!host.querySelector('.daily-shell')){
 host.innerHTML=`<div class="daily-shell"><div class="daily-top"><strong>Today <span id="daily-count"></span></strong><span id="daily-remaining"></span><span id="daily-percent"></span><span id="daily-countdown"></span><span id="daily-rate"></span><span id="daily-pace"></span><button id="daily-toggle" aria-controls="daily-details">More ▾</button></div><div class="daily-tracks"><label>Questions <progress id="question-progress" max="100"></progress></label><label>Time <progress id="time-progress" max="100"></progress></label></div><div id="micro-summary" hidden><strong id="micro-status"></strong><span id="micro-count"></span><span id="micro-clock"></span><progress id="micro-progress" max="100" aria-label="Micro target progress"></progress></div><div id="daily-details" hidden><form id="daily-form"><label>Daily target<input id="daily-target" type="number" min="1" max="100000" required></label><label>Start<input id="daily-start" type="time" required></label><label>Deadline<input id="daily-deadline" type="time" required></label><button class="primary">Save schedule</button></form><form id="micro-form"><label>Micro target · questions<input id="micro-questions" type="number" min="5" max="100000" step="5" value="25" required></label><label>Time · minutes<input id="micro-minutes" type="number" min="1" max="1440" step="1" value="30" required></label><button id="micro-start" class="primary">Start micro target</button><button id="micro-clear" type="button" hidden>Clear</button></form></div></div>`;
 $('#daily-toggle').onclick=()=>{dailyExpanded=!dailyExpanded;updateDaily()};
 $('#daily-target').value=s.config.target;$('#daily-start').value=s.config.start;$('#daily-deadline').value=s.config.deadline;
 $('#micro-questions').value=data.micro_target?.target||25;$('#micro-minutes').value=data.micro_target?.minutes||30;
 $('#micro-form').onsubmit=async e=>{e.preventDefault();if(saving)return;let next;try{next=MicroTarget.create($('#micro-questions').value,$('#micro-minutes').value,DailyProgress.events(data))}catch(err){notify(err.message);return}await saveMicroTarget(next)};
 $('#micro-clear').onclick=()=>{if(!saving)saveMicroTarget(null)};
 $('#daily-form').onsubmit=async e=>{e.preventDefault();if(saving)return;const target=Number($('#daily-target').value),start=$('#daily-start').value,deadline=$('#daily-deadline').value;if(!Number.isInteger(target)||target<1||deadline<=start)return notify('Use a positive target and a deadline after the start time.');const old=data.daily_settings;data.daily_settings={target,start,deadline};saving=true;try{await persist();notify('Daily schedule saved.')}catch(err){data.daily_settings=old;notify(err.message)}finally{saving=false;updateDaily()}};
 }
 $('#daily-count').textContent=`${s.completed} / ${s.config.target}`;$('#daily-remaining').textContent=`${s.remaining} remaining`;$('#daily-percent').textContent=`${s.percent.toFixed(1)}%`;$('#daily-countdown').textContent=s.overdue?'Deadline passed':`${hours}h ${minutes}m left`;
 $('#daily-rate').textContent=s.required===null?'Deadline reached':`${s.required.toFixed(1)} questions/h${s.beforeStart?' from start':''}`;$('#daily-pace').textContent=schedule;$('#daily-pace').className=s.remaining===0||s.delta>=0?'pace-ahead':'pace-behind';$('#question-progress').value=Math.min(100,s.percent);$('#time-progress').value=s.elapsed;$('#daily-details').hidden=!dailyExpanded;$('#daily-toggle').textContent=dailyExpanded?'Less ▴':'More ▾';$('#daily-toggle').setAttribute('aria-expanded',dailyExpanded);updateMicroTarget();
}
setInterval(updateDaily,1000);

function download(name,body,type){const u=URL.createObjectURL(new Blob([body],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
$('#home').onclick=render;$('#backup').onclick=()=>download(`anki-backup-${today()}.json`,JSON.stringify(data,null,2),'application/json');$('#restore').onclick=()=>$('#restore-file').click();$('#restore-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{const backup=JSON.parse(await file.text());if(!['decks','cards','attempts'].every(k=>Array.isArray(backup[k])))throw Error('Invalid backup format');confirmAction('Restore this backup?','This replaces the local workspace. Download a current backup first if needed.',async()=>{await request('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(backup)});data=backup;render();notify('Backup restored.')})}catch(err){notify(err.message)}e.target.value=''};
$('#upload').onchange=async e=>{const f=e.target.files[0];if(!f)return;notify('Importing deck…');try{data=await request('/api/import',{method:'POST',headers:{'X-Deck-Name':encodeURIComponent(f.name.replace(/\.apkg$/i,''))},body:f});render();notify('Deck imported successfully.')}catch(err){notify(err.message)}e.target.value=''};
request('/api/data').then(d=>{data=d;render()}).catch(e=>notify('Could not load workspace: '+e.message));

window.addEventListener('pagehide',stopReading);



$('#anki-sync').onclick=async()=>{
 const button=$('#anki-sync');button.disabled=true;button.textContent='Syncing…';
 try{const result=await request('/api/anki/sync',{method:'POST'});if(!result.connected)throw Error(result.error);notify(`Anki: ${result.matched} matched notes, ${result.updated} updated, ${result.unmatched} unmatched. ${result.reviews_synced_total||0} reviews synced to Anki history.${result.reviews_uncertain?' Some scheduler submissions need checking; they were not repeated.':''}`)}catch(e){notify(e.message)}finally{button.disabled=false;button.textContent='Sync Anki'}
};
