(function(root){
 function calculate(attempts){
  const unique=[...new Map(attempts.filter(a=>typeof a.is_correct==='boolean').map(a=>[a.id,a])).values()];
  const attempted=unique.length,correct=unique.filter(a=>a.is_correct).length,wrong=attempted-correct;
  return {attempted,correct,wrong,percent:attempted?correct/attempted*100:null,exam:correct-wrong*0.25};
 }
 const api={calculate};if(typeof module!=='undefined')module.exports=api;else root.ExamScoring=api;
})(typeof window==='undefined'?{}:window);
