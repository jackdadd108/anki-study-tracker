(function(root){
const zone='Asia/Kathmandu', defaults={target:300,start:'06:00',deadline:'22:00'};
function nepalDay(date=new Date()){return new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(date))}
function settings(value={}){return {target:Number.isInteger(Number(value.target))&&Number(value.target)>0?Number(value.target):300,start:/^\d\d:\d\d$/.test(value.start||'')?value.start:defaults.start,deadline:/^\d\d:\d\d$/.test(value.deadline||'')?value.deadline:defaults.deadline}}
function events(data){const seen=new Set(),prior=new Set();return [...(data.attempts||[]),...(data.daily_completions||[])].sort((a,b)=>a.answered_at.localeCompare(b.answered_at)).filter(e=>{if(seen.has(e.id))return false;seen.add(e.id);return true}).map(e=>{const key=e.deck_id+':'+e.card_id,kind=e.study_kind||(prior.has(key)?'revision':'new');prior.add(key);return {...e,study_kind:kind}})}
function stats(data,now=new Date()){
 const config=settings(data.daily_settings),day=nepalDay(now),all=events(data),daily=all.filter(e=>nepalDay(e.answered_at)===day),completed=daily.length,remaining=Math.max(0,config.target-completed),start=new Date(day+'T'+config.start+':00+05:45'),end=new Date(day+'T'+config.deadline+':00+05:45'),duration=end-start;
 const elapsed=Math.max(0,Math.min(1,(now-start)/duration)),left=Math.max(0,end-now),available=Math.max(0,end-Math.max(+now,+start)),expected=config.target*elapsed;
 return {day,config,completed,remaining,newCount:daily.filter(e=>e.study_kind==='new').length,revisionCount:daily.filter(e=>e.study_kind==='revision').length,percent:completed/config.target*100,elapsed:elapsed*100,left,required:remaining===0?0:available>0?remaining/(available/3600000):null,delta:completed-expected,beforeStart:now<start,overdue:now>=end,history:[...new Set(all.map(e=>nepalDay(e.answered_at)))].sort().reverse().filter(d=>d!==day).slice(0,7).map(d=>({day:d,count:all.filter(e=>nepalDay(e.answered_at)===d).length}))};
}
function kind(data,card){return events(data).some(e=>e.card_id===card.id&&e.deck_id===card.deck_id)?'revision':'new'}
const api={nepalDay,settings,events,stats,kind};if(typeof module!=='undefined')module.exports=api;else root.DailyProgress=api;
})(typeof window==='undefined'?{}:window);
