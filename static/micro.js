(function(root){
 function create(target,minutes,events,now=Date.now()){
  target=Number(target);minutes=Number(minutes);
  if(!Number.isInteger(target)||target<5||target>100000||target%5!==0)throw Error('Choose questions in increments of 5 (5, 10, 15…).');
  if(!Number.isInteger(minutes)||minutes<1||minutes>1440)throw Error('Choose a time from 1 to 1440 minutes.');
  return {target,minutes,start:now,end:now+minutes*60000,baseline:events.map(e=>e.id)};
 }
 function stats(state,events,now=Date.now()){
  if(!state)return null;
  const seen=new Set(state.baseline),until=Math.min(now,state.end);
  const completed=events.filter(e=>{const time=Date.parse(e.answered_at);if(seen.has(e.id)||time<state.start||time>until)return false;seen.add(e.id);return true}).length;
  return {completed,remaining:Math.max(0,state.target-completed),percent:Math.min(100,completed/state.target*100),left:Math.max(0,state.end-now),reached:completed>=state.target,expired:now>=state.end};
 }
 const api={create,stats};if(typeof module!=='undefined')module.exports=api;else root.MicroTarget=api;
})(typeof window==='undefined'?{}:window);
