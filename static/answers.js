(function(root){
function normalize(value){const items=Array.isArray(value)?value:String(value||'').split(/[\s,;&/+]+/);return [...new Set(items.map(s=>String(s).trim().toUpperCase()).filter(s=>/^[A-Z]$/.test(s)))].sort()}
function resolve(card,options){
 const valid=key=>normalize(key).filter(letter=>letter.charCodeAt(0)-65<options.length);
 if(card.edited_correct_option)return valid(card.correct_options||card.correct_option);
 const header=String(card.answer||'').split(/\n\s*\n/)[0].trim(),text=s=>String(s).toLowerCase().replace(/[.\s]+$/,'').trim();
 const exact=options.findIndex(o=>text(o)===text(header));if(exact>=0)return [String.fromCharCode(65+exact)];
 const lettersOnly=header.replace(/^(?:correct answers?|answers?)\s*[:=-]\s*/i,'');
 if(/^[A-Z](?:(?:\s*[,;&/+]+\s*|\s+and\s+)[A-Z])*[.]?$/i.test(lettersOnly))return valid(lettersOnly.replace(/\band\b/gi,',').replace(/[.]$/,''));
 const markers=[...header.matchAll(/(?:^|[,;\n]\s*)([A-Z])[.):]\s+/g)].map(m=>m[1]);
 const found=valid(markers);if(found.length)return found;
 return valid(card.correct_options||card.correct_option);
}
function grade(selected,correct){const a=normalize(selected),b=normalize(correct);return a.length===1&&b.includes(a[0])}
const api={normalize,resolve,grade};if(typeof module!=='undefined')module.exports=api;else root.AnswerKey=api;
})(typeof window==='undefined'?{}:window);
