const assert=require('assert/strict'),fs=require('fs'),path=require('path'),a=require('../static/answers.js');
for(const f of JSON.parse(fs.readFileSync(path.join(__dirname,'multi-answer-fixtures.json'))))assert.deepEqual(a.resolve(f.card,f.card.options),f.expected,f.name);
assert.equal(a.grade('D','A,C,D'),true);assert.equal(a.grade('C','A,C,D'),true);assert.equal(a.grade('A,B,C,D','A,C,D'),false);assert.equal(a.grade('B','A,C,D'),false);
console.log('Multi-answer parsing and any-valid-choice grading passed.');
