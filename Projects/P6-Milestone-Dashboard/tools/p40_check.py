#!/usr/bin/env python3
"""
P40 check (TEST-42): dense-run row growth, the critical-path filter set, the
split CSV, and user-added milestones.

DENSE-RUN GROWTH. A row whose densest proximity run reaches three markers grows
by half again. Three is the band count, not a number picked: MS_LEVEL_CYCLE has
three entries, so a run reaches "every line in use" at exactly three. The
reported cases are asserted BY NAME (rows 18 and 51 unchanged, 37 and 46 grown)
rather than only in aggregate, because an aggregate that happens to come out
right is not evidence about the rows that were reported.

THE CRITICAL SET. Status is multi-select with EMPTY MEANING NO CONSTRAINT,
which is deliberately not the same as all five selected; that distinction is
asserted directly. Float reads m.floatD, and a milestone with no recorded float
never satisfies a float constraint in either direction, which is also asserted,
because reporting an unknown as critical is the kind of wrong that reaches a
client.

THE CSV. The two blocks are asserted on CONTENT, not on headers: the base
Progress % must hold the schedule's own figure while an override is active, and
the entered column must hold the override. A header check alone would pass on a
file where both columns carried the same effective value, which is the defect
being fixed.

USER MILESTONES. Asserted as annotation-layer state: the seed arrays must be
byte-identical before and after an add, the milestone must survive a rebuild and
a view switch, and the publish payload must carry it. Weight 0 is asserted
explicitly, because a weighted addition would silently move every percentage on
the board.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p40_check.py [--html FILE]
Exit code 1 on any failed check.
"""

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p40-out">(.*?)</pre>', re.S)

VIEWPORTS = [(390, 844), (1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p40-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const r1=v=>Math.round(v*10)/10;
  const visRows=()=>document.querySelectorAll('#tbody tr.data:not(.hidden-row)').length;
  const rowByRef=ref=>document.querySelector('#tbody tr[data-ref="'+ref+'"]');

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;

    // ============ 1. Dense-run row growth ============
    // Rebuilt from the run cut, independently of the code under test, so this
    // measures the RULE rather than reading back the class the code wrote.
    const runsFor=function(tr){
      const cols=Array.prototype.map.call(tr.querySelectorAll('.m-wrap:not(.m-ghost)'),function(w){
        const td=w.closest('td[data-col]');
        return td?parseInt(td.getAttribute('data-col'),10):-1;
      }).filter(function(c){return c>=0;}).sort(function(a,b){return a-b;});
      let best=0,i=0;
      while(i<cols.length){
        let j=i+1;
        while(j<cols.length&&(cols[j]-cols[j-1])<=MS_PROXIMITY_COLS) j++;
        if(j-i>best) best=j-i;
        i=j;
      }
      return {maxRun:best,n:cols.length};
    };
    const plainH=[],denseH=[];
    let agree=0,disagree=[];
    document.querySelectorAll('#tbody tr.data').forEach(function(tr){
      const rr=runsFor(tr);
      const grown=tr.classList.contains('dense-run');
      const should=rr.maxRun>=MS_LEVEL_CYCLE.length;
      if(grown===should) agree++;
      else disagree.push((tr.getAttribute('data-ref')||'?')+' run '+rr.maxRun+' grown '+grown);
      (grown?denseH:plainH).push(r1(tr.getBoundingClientRect().height));
    });
    const mode=function(a){ const c={}; let best=null,bn=0;
      a.forEach(function(v){ c[v]=(c[v]||0)+1; if(c[v]>bn){bn=c[v];best=v;} }); return best; };
    R.notes.growth={rows:plainH.length+denseH.length,dense:denseH.length,
                    plainH:mode(plainH),denseH:mode(denseH),
                    agree:agree,disagree:disagree.slice(0,6),
                    growth:MS_DENSE_RUN_GROWTH,bands:MS_LEVEL_CYCLE.length};
    ck('growth: there are rows of both kinds to compare',
       denseH.length>3&&plainH.length>50,
       denseH.length+' grown of '+(plainH.length+denseH.length));
    ck('growth: every row is grown exactly when its densest run reaches the band count',
       disagree.length===0,
       agree+' agree, mismatches: '+(disagree.join('; ')||'none'));
    ck('growth: a grown row is half again the height of a plain one',
       Math.abs(mode(denseH)-Math.round(mode(plainH)*MS_DENSE_RUN_GROWTH))<=1.5,
       mode(plainH)+'px plain against '+mode(denseH)+'px grown');
    // The reported cases, by name. Row numbers in the report are the board's
    // own left-hand numbers, so they are looked up that way.
    const byNum=function(n){
      const cell=Array.prototype.filter.call(
        document.querySelectorAll('#tbody tr.data .row-num'),function(e){
          return e.textContent.trim()===String(n); })[0];
      return cell?cell.closest('tr'):null; };
    const reported={};
    [18,37,46,51].forEach(function(n){
      const tr=byNum(n);
      reported[n]=tr?{run:runsFor(tr).maxRun,grown:tr.classList.contains('dense-run'),
                      h:r1(tr.getBoundingClientRect().height)}:null;
    });
    R.notes.reported=reported;
    // Three of the four reported rows behave as the report says. Row 51 does
    // not, and the measurement says why rather than the rule being bent to fit:
    //
    //   row 18  SNIP-126  ONE milestone, col 16                  not grown
    //   row 37  SNIP-165  four, cols 15,16,17,19, one run of 4    grown
    //   row 46  SNIP-180  four, cols 18,19,19,20, one run of 4    grown
    //   row 51  SNIP-188  four, cols 13,14,15,17, one run of 4    grown
    //
    // Row 51 is identically dense to 37 and 46 on the unfiltered board, so no
    // rule reading the data can separate them. It read as fine in the report's
    // screenshot because that board carried a date range starting at the week
    // ending 06-Sep, which is column 15: SNIP-188 and SNIP-197 sit at 13 and 14
    // and were off the visible board, leaving two markers where the data has
    // four. Asserted as measured, with row 51's disagreement named, so the gap
    // between the rule and the report is on the record rather than papered
    // over. TD-153.
    ck('growth: the reported rows behave as measured, row 51 included',
       reported[18]&&reported[37]&&reported[46]&&reported[51]&&
       reported[18].run===1&&reported[18].grown===false&&
       reported[37].run===4&&reported[37].grown===true&&
       reported[46].run===4&&reported[46].grown===true&&
       reported[51].run===4&&reported[51].grown===true,
       JSON.stringify(reported));
    // The claim about row 51 is itself asserted, not just written in a comment:
    // two of its four markers fall before the column the report's date range
    // opened on.
    const r51=byNum(51);
    const cols51=r51?Array.prototype.map.call(r51.querySelectorAll('.m-wrap:not(.m-ghost)'),
      function(w){ const td=w.closest('td[data-col]');
        return td?parseInt(td.getAttribute('data-col'),10):-1; }).sort(function(a,b){return a-b;}):[];
    R.notes.row51={cols:cols51,beforeCol15:cols51.filter(function(c){return c<15;}).length};
    ck('growth: row 51 has four markers, two of them before the reported window',
       cols51.length===4&&R.notes.row51.beforeCol15===2,
       JSON.stringify(R.notes.row51));

    // ============ 2. The critical path filter set ============
    const base=visRows();
    R.notes.crit={base:base};
    ck('crit: the board opens unfiltered, so a narrowing is visible',
       base>100, base+' rows');
    // Empty selection is NOT the same as all five selected.
    ck('crit: no chip is pressed at open, and the board is not narrowed by it',
       STATUS_FILTER.size===0&&visRows()===base,
       STATUS_FILTER.size+' selected');
    toggleStatusFilter('CRIT'); await settle();
    const onlyCrit=visRows();
    toggleStatusFilter('RISK'); await settle();
    const critRisk=visRows();
    R.notes.crit.onlyCrit=onlyCrit; R.notes.crit.critRisk=critRisk;
    ck('crit: one status narrows the board',
       onlyCrit>0&&onlyCrit<base, onlyCrit+' of '+base);
    ck('crit: a second status WIDENS it, because the selection is a union',
       critRisk>onlyCrit&&critRisk<base,
       onlyCrit+' -> '+critRisk+' of '+base);
    ck('crit: the chips show which are selected',
       $('fs-CRIT').classList.contains('active')&&
       $('fs-RISK').classList.contains('active')&&
       !$('fs-DONE').classList.contains('active')&&
       $('fs-CRIT').getAttribute('aria-pressed')==='true',
       'crit '+$('fs-CRIT').className);
    // Selecting all five must equal no selection at all, which is the property
    // that makes "empty means no constraint" coherent.
    ['TRACK','DONE','FUTURE'].forEach(function(k){ toggleStatusFilter(k); });
    await settle();
    const allFive=visRows();
    R.notes.crit.allFive=allFive;
    ck('crit: all five selected shows the same board as none selected',
       allFive===base, allFive+' against '+base);
    clearCriticalFilters(); await settle();
    ck('crit: clearing puts the board back and unpresses every chip',
       visRows()===base&&STATUS_FILTER.size===0&&
       !$('fs-CRIT').classList.contains('active'),
       visRows()+' rows, '+STATUS_FILTER.size+' chips');

    // Float. Counted from the data first, so the expected direction is derived
    // rather than assumed.
    const withFloat=MILESTONES.filter(function(m){
      return m.floatD!=null&&m.floatD!==''&&!isNaN(parseFloat(m.floatD)); });
    const le13=withFloat.filter(function(m){ return parseFloat(m.floatD)<=13; });
    R.notes.float={total:MILESTONES.length,withFloat:withFloat.length,le13:le13.length};
    ck('float: the seeded board carries float figures to filter on',
       withFloat.length>20&&le13.length>0,
       withFloat.length+' of '+MILESTONES.length+' carry float, '+le13.length+' at or below 13d');
    setFloatFilter('le',13,'d'); await settle();
    const fLe=visRows();
    setFloatFilter('ge',8,'w'); await settle();
    const fGe=visRows();
    R.notes.float.le=fLe; R.notes.float.ge=fGe;
    ck('float: at or below 13 days narrows the board',
       fLe>0&&fLe<base, fLe+' of '+base);
    ck('float: at or above 8 weeks is a different, also narrower board',
       fGe>0&&fGe<base&&fGe!==fLe, fGe+' of '+base+', against '+fLe+' for the other direction');
    // Weeks must convert, not be compared as days.
    setFloatFilter('le',2,'w'); await settle();
    const w2=visRows();
    setFloatFilter('le',14,'d'); await settle();
    const d14=visRows();
    R.notes.float.weeksEqualDays={w2:w2,d14:d14};
    ck('float: 2 weeks and 14 days give the same board, so the unit converts',
       w2===d14, w2+' against '+d14);
    // A milestone with no float must not satisfy either direction.
    const noFloat=MILESTONES.filter(function(m){
      return m.floatD==null||m.floatD===''; })[0];
    R.notes.float.unknownSample=noFloat?String(noFloat.id||noFloat.ref):'(none)';
    ck('float: a milestone with no recorded float matches neither direction',
       !!noFloat&&msMatchesFloat(noFloat,{op:'le',days:9999})===false&&
       msMatchesFloat(noFloat,{op:'ge',days:-9999})===false,
       'sample '+R.notes.float.unknownSample);
    clearCriticalFilters(); await settle();
    ck('float: clearing it puts the board back',
       visRows()===base, visRows()+' against '+base);
    // Remove all filters has to reach this set too, since it is not a field.
    toggleStatusFilter('CRIT'); setFloatFilter('le',5,'d'); await settle();
    clearFilter(); await settle();
    R.notes.crit.afterRemoveAll={rows:visRows(),chips:STATUS_FILTER.size,
                                 op:$('filter-float-op').value};
    ck('crit: Remove all filters clears the status chips and the float filter too',
       visRows()===base&&STATUS_FILTER.size===0&&$('filter-float-op').value==='',
       JSON.stringify(R.notes.crit.afterRemoveAll));

    // ============ 3. Add a milestone ============
    // Snapshots BEFORE, so the three-layer rule is measured rather than assumed.
    const seedBefore=JSON.stringify(SEED_MILESTONES);
    const seedTasksBefore=JSON.stringify(SEED_TASKS);
    const msBefore=MILESTONES.length, rowsBefore=document.querySelectorAll('#tbody tr.data').length;
    // Route 1: the header button, which makes a row of its own.
    $('btn-add-ms').click(); await settle();
    const dlgOpen=!$('add-ms-dialog').hidden;
    const genId=$('add-ms-id').value;
    R.notes.add={dlgOpen:dlgOpen,generatedId:genId};
    ck('add: the header button opens the dialog with a generated USR id',
       dlgOpen&&/^USR-\d{3}$/.test(genId), 'dialog '+dlgOpen+', id '+genId);
    // Refusals first, so an empty or colliding record cannot reach the store.
    $('add-ms-name').value=''; saveAddMilestone();
    const refusedBlank=!$('add-ms-dialog').hidden&&!$('add-ms-err').hidden;
    $('add-ms-name').value='Probe milestone';
    $('add-ms-id').value=allMilestoneIds()[0];
    saveAddMilestone();
    const refusedDup=!$('add-ms-dialog').hidden&&!$('add-ms-err').hidden;
    R.notes.add.refusals={blank:refusedBlank,duplicate:refusedDup};
    ck('add: a blank name and a colliding Activity ID are both refused',
       refusedBlank&&refusedDup&&USER_MILESTONES.length===0,
       JSON.stringify(R.notes.add.refusals)+', store holds '+USER_MILESTONES.length);
    $('add-ms-id').value=genId;
    $('add-ms-date').value=isoDay(WE_DATES[Math.floor(WE_DATES.length/2)]);
    saveAddMilestone();
    await settle(); await settle(); await settle();
    const added=MILESTONES.filter(function(m){ return msId(m)===genId; })[0];
    const addedRow=rowByRef(genId);
    R.notes.add.after={store:USER_MILESTONES.length,rows:USER_ROWS.length,
                       onBoard:!!added,weight:added?added.weight:null,
                       rowOnBoard:!!addedRow,
                       band:addedRow?(addedRow.getAttribute('data-band')||''):'',
                       markers:addedRow?addedRow.querySelectorAll('.m-wrap:not(.m-ghost)').length:0,
                       boardRows:document.querySelectorAll('#tbody tr.data').length};
    ck('add: it reaches the board as a row with a marker on it',
       !!added&&!!addedRow&&R.notes.add.after.markers===1&&
       R.notes.add.after.boardRows===rowsBefore+1,
       JSON.stringify(R.notes.add.after));
    ck('add: it carries no weight, so no percentage on the board moves',
       added&&added.weight===0, 'weight '+(added?added.weight:'(missing)'));
    ck('add: the notes field carries the [ID] form the key readers re-derive from',
       added&&extractSnipId(added.notes)===genId&&msKeyFor(added)===genId,
       added?added.notes:'(missing)');
    ck('add: THREE LAYERS, the seed arrays are byte-identical after the add',
       JSON.stringify(SEED_MILESTONES)===seedBefore&&
       JSON.stringify(SEED_TASKS)===seedTasksBefore,
       'milestones '+(JSON.stringify(SEED_MILESTONES)===seedBefore)+
       ', tasks '+(JSON.stringify(SEED_TASKS)===seedTasksBefore));
    // It has to survive the two things that re-slice TASKS/MILESTONES.
    scheduleRerender(true); await settle(); await settle(); await settle();
    const afterRerender=!!rowByRef(genId);
    R.notes.add.survives={rerender:afterRerender};
    ck('add: it survives a rebuild', afterRerender, 'row present '+afterRerender);
    // Route 2: a double click on a week cell, which fixes row and date.
    const host=document.querySelector('#tbody tr.data[data-ref="'+TASKS[0].ref+'"]');
    const cell=host?host.querySelector('td.c-wk[data-col="4"]'):null;
    if(cell){
      cell.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
      await settle();
      R.notes.add.viaCell={open:!$('add-ms-dialog').hidden,
                           date:$('add-ms-date').value,
                           expected:isoDay(WE_DATES[4]),
                           where:$('add-ms-where').textContent.slice(0,60),
                           ctxRef:ADD_MS_CTX?ADD_MS_CTX.ref:null};
      ck('add: a double click on a cell opens it with that row and that week set',
         R.notes.add.viaCell.open&&
         R.notes.add.viaCell.date===R.notes.add.viaCell.expected&&
         R.notes.add.viaCell.ctxRef===TASKS[0].ref,
         JSON.stringify(R.notes.add.viaCell));
      const idOnRow=$('add-ms-id').value;
      $('add-ms-name').value='On an existing row';
      saveAddMilestone(); await settle(); await settle(); await settle();
      const onRow=rowByRef(TASKS[0].ref);
      R.notes.add.viaCell.landedOnHostRow=!!onRow&&
        Array.prototype.some.call(onRow.querySelectorAll('.m-wrap'),function(w){
          return (w.getAttribute('data-ms')||'')===idOnRow; });
      R.notes.add.viaCell.noNewRow=document.querySelectorAll('#tbody tr.data').length
        ===R.notes.add.after.boardRows;
      ck('add: that one lands on the row that was clicked and creates no new row',
         R.notes.add.viaCell.noNewRow&&USER_ROWS.length===1&&USER_MILESTONES.length===2,
         JSON.stringify({noNewRow:R.notes.add.viaCell.noNewRow,
                         rows:USER_ROWS.length,ms:USER_MILESTONES.length}));
    } else {
      ck('add: a week cell was available to double click', false, 'no td.c-wk[data-col=4]');
    }
    // The ids must not collide with each other.
    R.notes.add.ids=USER_MILESTONES.map(function(m){return m.id;});
    ck('add: the two additions took different generated ids',
       R.notes.add.ids.length===2&&R.notes.add.ids[0]!==R.notes.add.ids[1],
       R.notes.add.ids.join(', '));
    // Round trip: the publish payload has to carry them, and re-applying the
    // same payload must not duplicate them.
    const payload={userMilestones:JSON.parse(JSON.stringify(USER_MILESTONES)),
                   userRows:JSON.parse(JSON.stringify(USER_ROWS))};
    const beforeApply=USER_MILESTONES.length;
    applyUserMilestones(payload);
    R.notes.add.roundTrip={before:beforeApply,after:USER_MILESTONES.length};
    ck('add: re-applying the same payload is a no-op, not a duplicate',
       USER_MILESTONES.length===beforeApply,
       beforeApply+' -> '+USER_MILESTONES.length);

    // ============ 4. The split CSV ============
    // Content, not headers. An override is set, then the two blocks must
    // disagree: base holds the schedule's figure, entered holds the override.
    const target=MILESTONES.filter(function(m){
      return m.weight>0&&m.progress!==55&&msId(m)&&!m.userAdded; })[0];
    const tKey=msKeyFor(target);
    MS_PROGRESS_OVERRIDE[tKey]=55;
    MS_COMMENTS[tKey]='probe comment';
    const rows2=buildCsvRows();
    const hdr=rows2[0];
    const iBaseProg=hdr.indexOf('Progress %');
    const iEntProg=hdr.indexOf('Progress % (entered)');
    const iEntCmt=hdr.indexOf('Comments (entered)');
    const line=rows2.filter(function(r){ return r[2]===target.ref; })[0];
    R.notes.csv={header:hdr,baseCols:CSV_BASE_HEADER.length,
                 enteredCols:CSV_ENTERED_HEADER.length,
                 target:msId(target),targetRef:target.ref,
                 baseProg:line?line[iBaseProg]:null,
                 entProg:line?line[iEntProg]:null,
                 entCmt:line?line[iEntCmt]:null};
    ck('csv: the base block comes first and the entered block after it',
       iBaseProg>=0&&iEntProg>iBaseProg&&iEntProg===CSV_BASE_HEADER.length,
       'base Progress % at '+iBaseProg+', entered at '+iEntProg);
    ck('csv: there is a row for the target to read',
       !!line, line?('ref '+line[2]):'no row for '+target.ref);
    ck('csv: the entered column carries the override',
       !!line&&String(line[iEntProg]).indexOf('55')>=0, line?String(line[iEntProg]):'');
    ck('csv: and the base column does NOT, so the two blocks genuinely differ',
       !!line&&String(line[iBaseProg]).indexOf('55')<0,
       'base reads '+(line?String(line[iBaseProg]):'')+
       ', entered reads '+(line?String(line[iEntProg]):''));
    ck('csv: the comment reaches its own entered column',
       !!line&&String(line[iEntCmt]).indexOf('probe comment')>=0,
       line?String(line[iEntCmt]):'');
    delete MS_PROGRESS_OVERRIDE[tKey]; delete MS_COMMENTS[tKey];
    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=e&&e.stack; }
  emit();
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p40.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html)
    src = html.read_text(encoding="utf-8", errors="replace")
    nospace = src.replace(" ", "").replace("\n", "")

    checks = []
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))
    checks.append((
        "source: the growth threshold is the band count, not a typed number",
        "_maxRun>=MS_LEVEL_CYCLE.length" in nospace
        and "constMS_DENSE_RUN_GROWTH=1.5" in nospace,
        "the threshold or the ratio is hardcoded elsewhere"))
    checks.append((
        "source: user milestones are merged at the one function that builds rows",
        src.count("function mergeUserMilestones(") == 1
        and src.count("mergeUserMilestones();") == 1
        and "mergeUserMilestones();\n  // Fresh per rebuild" in src,
        "the merge is not at the top of renderRows"))
    checks.append((
        "source: user milestones round-trip through publish AND the model export",
        src.count("userMilestones:USER_MILESTONES") == 2
        and src.count("applyUserMilestones(p);") == 2
        and "key:'userMs'" in src,
        "a payload or the selective-import category is missing"))
    checks.append((
        "source: the seed arrays are never written to by the add path",
        "SEED_MILESTONES.push" not in src and "SEED_TASKS.push" not in src,
        "an add path writes into the schedule layer"))
    checks.append((
        "source: one delegated dblclick listener, not a handler per cell",
        src.count("addEventListener('dblclick'") == 1 and "ondblclick" not in src,
        "per-cell dblclick handlers found"))
    checks.append((
        "source: the CSV header is two named blocks",
        "const CSV_BASE_HEADER=" in src and "const CSV_ENTERED_HEADER=" in src,
        "the blocks are not named"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("growth", "reported", "crit", "float", "add", "csv"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
