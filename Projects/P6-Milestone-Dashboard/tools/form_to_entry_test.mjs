import {createRequire} from 'node:module';
const {formToEntry}=createRequire(import.meta.url)('../src/modules/notes-card/form-to-entry.js');
let fails=0, n=0;
function ok(name,cond,extra){ n++; if(cond) console.log('PASS '+name); else { fails++; console.log('FAIL '+name+(extra?' '+JSON.stringify(extra):'')); } }

const base={title:'Pour slab',shortTitle:'Slab',start:'2026-10-01',date:'2026-10-09',weight:'10',floatD:'3',
  type:'finish',marker:'diamond',progress:'40',comment:'',health:-1};
const own={actName:'Pour slab',start:'2026-10-01',date:'2026-10-09',weight:10,floatD:3,type:'finish',marker:'diamond',progress:40,health:-1};
const ctx=function(o){ return Object.assign({key:'M1',
  own:f=>own[f], current:f=>own[f], scheduleProgress:50, floatReadOnly:false,
  parseDate:s=>{ const m=/^(\d{4})-(\d\d)-(\d\d)$/.exec(s); return m?s:(s==='9-Oct-26'?'2026-10-09':null); }},o||{}); };
const run=(clean,patch,c)=>formToEntry(clean,Object.assign({},clean,patch),ctx(c));

// every field type
let r=run(base,{title:'New name'});
ok('title -> actName', r.draft.changes.actName.to==='New name'&&r.draft.changes.actName.from==='Pour slab', r);
r=run(base,{date:'2026-10-12'}); ok('date', r.draft.changes.date.to==='2026-10-12'&&r.draft.changes.date.from==='2026-10-09');
r=run(base,{start:'2026-10-02'}); ok('start', r.draft.changes.start.to==='2026-10-02');
r=run(base,{weight:'12.5'}); ok('weight parseFloat', r.draft.changes.weight.to===12.5);
r=run(base,{floatD:'7'}); ok('floatD', r.draft.changes.floatD.to===7);
r=run(base,{type:'start'}); ok('type', r.draft.changes.type.to==='start');
r=run(base,{marker:'square'}); ok('marker', r.draft.changes.marker.to==='square');
r=run(base,{progress:'70'}); ok('progress', r.draft.changes.progress.to===70&&r.draft.changes.progress.from===40);
r=run(base,{health:2}); ok('health', r.draft.changes.health.to===2);
r=run(base,{title:'X',weight:'11'}); ok('two fields at once', Object.keys(r.draft.changes).length===2);
r=run(base,{title:'  '},{current:f=>f==='actName'?'Renamed':own[f]}); ok('blank title -> null', r.draft.changes.actName.to===null);
r=run(base,{title:'Pour slab '}); ok('title trimmed equal to own, card showed own -> dropped', r===null, r);

// shape
r=run(base,{title:'N',comment:'  hello  '});
ok('draft shape', JSON.stringify(Object.keys(r.draft))===JSON.stringify(['target','text','changes','origin','status'])&&
  r.draft.target.kind==='ms'&&r.draft.target.key==='M1'&&r.draft.origin==='card'&&r.draft.status==='open');
ok('both together, text trimmed', r.draft.text==='hello'&&!!r.draft.changes.actName);

// remark only / changes only / nothing
r=run(base,{comment:'Waiting on concrete'}); ok('remark only', r.draft.text==='Waiting on concrete'&&Object.keys(r.draft.changes).length===0);
r=run(base,{weight:'11'}); ok('changes only, empty text', r.draft.text===''&&!!r.draft.changes.weight);
ok('no change -> null', run(base,{})===null);
ok('whitespace-only remark, no change -> null', run(base,{comment:'   '})===null);
const carried=Object.assign({},base,{comment:'old remark'});
ok('untouched carried remark -> null', run(carried,{})===null);
r=run(carried,{comment:'old remark and more'}); ok('edited remark is new', r&&r.draft.text==='old remark and more');
r=run(carried,{weight:'11'}); ok('carried remark + change keeps draft text as spec (see notes)', r&&r.draft.text==='old remark'&&!!r.draft.changes.weight);

// revert
ok('typed then reverted -> null (now equals clean)', run(base,{weight:'11'})!==null&&run(base,{weight:'10'})===null);
r=run(base,{weight:'10.0'}); ok('touched but same number as from -> dropped', r===null, r);
r=run(base,{date:'9-Oct-26'}); ok('different format, same date -> dropped', r===null, r);
r=run(base,{date:'9-Oct-26',comment:'x'}); ok('dropped change leaves remark', r&&!r.draft.changes.date);

// dates
ok('blank date -> to null when card showed an override',
  run(base,{date:''},{current:f=>f==='date'?'2026-10-20':own[f]}).draft.changes.date.to===null);
ok('blank date when card already showed schedule -> dropped', run(base,{date:''})===null);
r=run(base,{date:'garbage',weight:'11'}); ok('unparseable date skipped', !r.draft.changes.date&&!!r.draft.changes.weight);
ok('unparseable date alone -> null', run(base,{date:'garbage'})===null);
ok('to equals from dropped', run(base,{start:'2026-10-05'},{current:f=>f==='start'?'2026-10-05':own[f]})===null);
r=run(Object.assign({},base,{date:'2026-10-30'}),{date:'2026-10-09'},{current:f=>f==='date'?'2026-10-30':own[f]});
ok('value equal to own -> to null', r.draft.changes.date.to===null&&r.draft.changes.date.from==='2026-10-30');

// progress boundaries: schedule 50; current shown 40
const P=v=>run(base,{progress:v});
ok('progress 0', P('0').draft.changes.progress.to===0);
ok('progress 1 (just above 0)', P('1').draft.changes.progress.to===1);
ok('progress -1 clamps to 0', P('-1').draft.changes.progress.to===0);
ok('progress 99', P('99').draft.changes.progress.to===99);
ok('progress 100', P('100').draft.changes.progress.to===100);
ok('progress 101 clamps to 100', P('101').draft.changes.progress.to===100);
ok('progress 102 clamps to 100', P('102').draft.changes.progress.to===100);
ok("progress '45%'", P('45%').draft.changes.progress.to===45);
ok('progress 44.6 rounds to 45', P('44.6').draft.changes.progress.to===45);
ok('progress blank -> null (card showed override 40)', P('').draft.changes.progress.to===null);
ok('progress NaN text -> null', P('abc').draft.changes.progress.to===null);
ok('progress == schedule (50) -> null', P('50').draft.changes.progress.to===null);
ok('progress 49 not schedule', P('49').draft.changes.progress.to===49);
ok('progress 51 not schedule', P('51').draft.changes.progress.to===51);
ok('progress 100 == schedule 100 -> null', run(base,{progress:'100'},{scheduleProgress:100}).draft.changes.progress.to===null);
ok('progress blank when current is schedule -> dropped', run(base,{progress:''},{current:f=>f==='progress'?50:own[f]})===null);

// health
const H=(clean,v,c)=>run(Object.assign({},base,clean),{health:v},c);
r=H({health:2},-1,{current:f=>f==='health'?2:own[f]});
ok('health -1 -> null', r.draft.changes.health.to===null&&r.draft.changes.health.from===2, r);
ok('health 0 is real, not null', H({},0).draft.changes.health.to===0);
ok('health 1', H({},1).draft.changes.health.to===1);
ok('health 3', H({},3).draft.changes.health.to===3);
ok('health 4', H({},4).draft.changes.health.to===4);
ok('health -1 from -1 untouched -> null', H({},-1)===null);
ok('health 0 with current -1 not dropped', H({},0)!==null);
ok('health equal to current dropped', run(base,{health:3},{current:f=>f==='health'?3:own[f]})===null);

// float
r=run(base,{floatD:'9',weight:'11'},{floatReadOnly:true}); ok('floatReadOnly excludes floatD', !r.draft.changes.floatD&&!!r.draft.changes.weight);
r=run(base,{floatD:'9',weight:'11'},{floatReadOnly:false}); ok('float editable includes floatD', !!r.draft.changes.floatD);
ok('floatReadOnly alone -> null', run(base,{floatD:'9'},{floatReadOnly:true})===null);
ok('float blank -> null (override shown)', run(base,{floatD:''},{current:f=>f==='floatD'?8:own[f]}).draft.changes.floatD.to===null);

// weight NaN and boundaries around own=10
r=run(base,{weight:'abc'},{current:f=>f==='weight'?15:own[f]}); ok('weight NaN -> null', r.draft.changes.weight.to===null);
ok('weight NaN, card showed schedule -> dropped', run(base,{weight:'abc'})===null);
ok('weight equal to own 10, card showed 10 -> dropped', run(base,{weight:'10'})===null);
r=run(Object.assign({},base,{weight:'15'}),{weight:'10'},{current:f=>f==='weight'?15:own[f]});
ok('weight back to own -> to null from 15', r.draft.changes.weight.to===null&&r.draft.changes.weight.from===15, r);
ok('weight 9 and 11 either side of own 10', run(base,{weight:'9'}).draft.changes.weight.to===9&&run(base,{weight:'11'}).draft.changes.weight.to===11);

// shortTitle
r=run(base,{shortTitle:'Slab2',weight:'11'}); ok('shortTitle returned separately', r.shortTitle==='Slab2'&&!('shortTitle' in r.draft.changes));
r=run(base,{weight:'11'}); ok('shortTitle null when unchanged', r.shortTitle===null);
r=run(base,{shortTitle:'Slab2'}); ok('shortTitle only -> draft null, shortTitle kept', r&&r.draft===null&&r.shortTitle==='Slab2');
r=run(base,{shortTitle:''}); ok('shortTitle cleared -> empty string', r&&r.shortTitle==='');

// P69: the A flag on each date (startActual -> startActual, dateActual -> actual)
const baseA=Object.assign({},base,{startActual:false,dateActual:false});
const ownA=f=>({actual:false,startActual:false})[f]!==undefined?({actual:false,startActual:false})[f]:own[f];
r=run(baseA,{dateActual:true},{own:ownA,current:ownA}); ok('finish marked actual', r.draft.changes.actual.to===true&&r.draft.changes.actual.from===false, r);
r=run(baseA,{startActual:true},{own:ownA,current:ownA}); ok('start marked actual', r.draft.changes.startActual.to===true&&!r.draft.changes.actual, r);
r=run(baseA,{date:'2026-10-12',dateActual:true},{own:ownA,current:ownA});
ok('new date saved as actual: two changes', r.draft.changes.date.to==='2026-10-12'&&r.draft.changes.actual.to===true);
const ownT=f=>f==='actual'?true:ownA(f);
const baseT=Object.assign({},baseA,{dateActual:true});
r=run(baseT,{dateActual:false},{own:ownT,current:ownT}); ok('schedule actual set back to forecast', r.draft.changes.actual.to===false&&r.draft.changes.actual.from===true, r);
const curT=f=>f==='actual'?false:ownT(f);
r=run(Object.assign({},baseT,{dateActual:false}),{dateActual:true},{own:ownT,current:curT});
ok('back to the schedule actual -> to null', r.draft.changes.actual.to===null, r);
r=run(Object.assign({},baseA,{date:'2026-10-20',dateActual:true}),{date:'',dateActual:false},{own:ownA,current:f=>f==='date'?'2026-10-20':(f==='actual'?true:ownA(f))});
ok('cleared date takes its flag back to schedule', r.draft.changes.date.to===null&&r.draft.changes.actual.to===null, r);
ok('flag untouched -> nothing', run(baseA,{},{own:ownA,current:ownA})===null);

console.log('\n'+(n-fails)+'/'+n+' passed');
process.exit(fails?1:0);
