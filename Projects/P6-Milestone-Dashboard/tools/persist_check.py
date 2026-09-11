#!/usr/bin/env python3
"""
Persistence round-trip check for the P6 Milestone Dashboard (TEST-23 / TD-58).

Asks one question in three places: when a user marks the board up, does every
kind of mark survive?

  Stage 1  Make one of every kind of edit against the real app, then call the
           real publishDashboard() and exportModel() and capture what they
           actually write. Nothing here reimplements a payload.
  Stage 2  Load the published file as a reader would and assert every edit is
           present, applied, and described correctly.
  Stage 3  Load a CLEAN app, feed it the exported model through the real
           selective-import categories, and assert the two replayed categories
           (milestone row moves, removed rows) land on a schedule that has
           never seen them. This is the case a merge cannot cover and the one
           TD-27 was open on.

Both downloads are captured by stubbing URL.createObjectURL at the app's
boundary with the browser. The app is otherwise untouched.

Note on stage 2: publishDashboard() strips every script that is not the app's
own, which includes this harness's probe. That is deliberate (TD-42), so the
stage 2 probe is re-injected here rather than surviving the publish.

Usage:
  python3 tools/persist_check.py [--html FILE] [--keep DIR]
Exit code 1 if any assertion fails.
"""

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome",
]

OUT_RE = re.compile(r'<pre id="persist-out">(.*?)</pre>', re.S)

# --------------------------------------------------------------------------
# Stage 1 — make every kind of edit, then capture both real downloads.
# --------------------------------------------------------------------------
STAGE1 = r"""
(function(){
  const R={ok:false,steps:[],err:null};
  function say(k,v){ R.steps.push(k+': '+v); }

  // Capture what the app writes, at its boundary with the browser.
  const CAP={};
  let capName=null;
  const realCreate=URL.createObjectURL;
  URL.createObjectURL=function(blob){ CAP[capName]=blob; return 'blob:captured'; };
  // publishDashboard/exportModel both call a.click() on a real anchor; with a
  // stubbed href that is inert, but block it anyway so nothing navigates.
  const realClick=HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click=function(){};

  function finish(){
    // Created only now. Appending it up front put an empty copy of this very
    // element into the published clone, and the stage 2 reader matched that
    // one rather than its own output.
    const out=document.createElement('pre'); out.id='persist-out';
    document.body.appendChild(out);
    // base64, because the captured file is itself HTML: round-tripping it
    // through the DOM's own entity escaping double-unescapes and corrupts it.
    out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    URL.createObjectURL=realCreate;
    HTMLAnchorElement.prototype.click=realClick;
  }

  try{
    window.confirm=function(){ return true; };

    // --- pick a milestone that carries a real id, and a different target row
    const withId=MILESTONES.filter(function(m){ return extractSnipId(m.notes); });
    if(!withId.length) throw new Error('no milestone carries a SNIP id');
    const ms=withId[0];
    const fromRef=ms.ref;
    const otherRow=TASKS.filter(function(t){ return t.ref!==fromRef; })[0];
    if(!otherRow) throw new Error('only one row on the board');
    R.msId=extractSnipId(ms.notes); R.fromRef=fromRef; R.toRef=otherRow.ref;
    say('picked milestone', R.msId+' on '+fromRef+' -> '+otherRow.ref);

    // --- 1. drag the milestone to another row (the real move path)
    moveMilestoneToRow(ms, otherRow.ref);

    // --- 2..4 annotations keyed to it, set after the move so the key is current
    const k=msKeyFor(ms);
    R.msKey=k;
    MS_COMMENTS[k]='PERSIST comment on a moved milestone';
    MS_HEALTH_OVERRIDE[k]=2;
    MS_SHORT_TITLES[k]='PERSIST-SHORT';

    // --- 5. a dependency-line comment, the kind neither payload carried
    const depKey='pred:'+R.msId+'->PERSIST-DEST';
    R.depKey=depKey;
    DEP_COMMENTS[depKey]='PERSIST dependency note';
    DEP_VIS[depKey]=true;

    setTimeout(function(){
     try{
      // --- 7 first: find the row that will be removed, so the override in
      // step 6 can deliberately avoid it. Overlapping the two edits on one row
      // made a correctly discarded override look like a lost one.
      const empty=TASKS.filter(function(t){ return !milestonesForRow(t.ref).length; })[0];
      const delRef=empty?empty.ref:null;

      // --- 6. row health and a remark, read back off the rendered rows
      const rows=Array.prototype.slice.call(document.querySelectorAll('tr[data-type="row"]'));
      const tr=rows.filter(function(x){ return x.getAttribute('data-ref')!==delRef; })[0];
      if(!tr) throw new Error('no row left to carry an override');
      R.ovRef=tr.getAttribute('data-ref');
      const dot=tr.querySelector('.health-dot');
      const orig=dot.getAttribute('data-orig-health');
      dot.setAttribute('data-current-health', String(orig)==='3'?'1':'3');
      const rm=tr.querySelector('.remarks');
      rm.textContent='PERSIST remark';
      say('row override on', R.ovRef);

      // --- 7. remove the empty row found above
      if(delRef){ R.delRef=delRef; deleteRow(delRef,null); say('deleted row', delRef); }
      else { say('deleted row','NONE AVAILABLE'); }

      setTimeout(function(){
       try{
        R.liveMoves=MS_MOVES.length;
        R.liveDeleted=DELETED_ROWS.length;
        R.liveMarkup=MARKUP_COUNT;

        capName='model'; exportModel();
        capName='published'; publishDashboard();

        const jobs=['model','published'].map(function(n){
          return CAP[n]?CAP[n].text().then(function(t){ R[n+'Text']=t; })
                       :Promise.reject(new Error('nothing captured for '+n));
        });
        Promise.all(jobs).then(function(){ R.ok=true; finish(); },
                               function(e){ R.err='capture: '+e.message; finish(); });
       }catch(e){ R.err=e.message+' @inner2'; finish(); }
      },300);
     }catch(e){ R.err=e.message+' @inner1'; finish(); }
    },300);
  }catch(e){ R.err=e.message+' @outer'; finish(); }
})();
"""

# --------------------------------------------------------------------------
# Stage 2 — read the published file back.
# --------------------------------------------------------------------------
STAGE2 = r"""
(function(){
  const out=document.createElement('pre'); out.id='persist-out'; document.body.appendChild(out);
  const R={ok:false,reached:'probe installed, first timer not fired'};
  function emit(){ out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); }
  emit();
  try{
    const E=JSON.parse(document.getElementById('persist-expect').textContent);
    setTimeout(function(){
      R.reached='first timer fired';
      try{
        R.depComment   = DEP_COMMENTS[E.depKey]||null;
        R.msComment    = MS_COMMENTS[E.msKey]||null;
        R.msHealth     = (E.msKey in MS_HEALTH_OVERRIDE)?MS_HEALTH_OVERRIDE[E.msKey]:null;
        R.msShortTitle = MS_SHORT_TITLES[E.msKey]||null;
        R.moves        = MS_MOVES.length;
        R.deleted      = DELETED_ROWS.length;
        R.markupCount  = MARKUP_COUNT;
        // Where the milestone actually sits in the published data, not where a
        // record says it should be.
        const m=MILESTONES.filter(function(x){ return extractSnipId(x.notes)===E.msId; })[0];
        R.msRef        = m?m.ref:null;
        R.delRowGone   = E.delRef? !TASKS.some(function(t){return t.ref===E.delRef;}) : null;
        const tr=document.querySelector('tr[data-ref="'+E.ovRef+'"]');
        const rm=tr?tr.querySelector('.remarks'):null;
        R.rowRemark    = rm?rm.textContent.trim():null;
        // Does the header describe the edits, rather than claiming there were none?
        const hdr=document.getElementById('sd-src-box');
        R.headerText   = hdr?hdr.textContent.trim():null;
        R.reached='complete';
        R.ok=true;
      }catch(e){ R.err=e.message; }
      emit();
    },400);
  }catch(e){ R.err=e.message; emit(); }
})();
"""

# --------------------------------------------------------------------------
# Stage 3 — replay the exported model onto a clean, unmodified board.
# --------------------------------------------------------------------------
STAGE3 = r"""
(function(){
  const out=document.createElement('pre'); out.id='persist-out'; document.body.appendChild(out);
  const R={ok:false,reached:'probe installed, first timer not fired'};
  function emit(){ out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); }
  emit();
  try{
    const E=JSON.parse(document.getElementById('persist-expect').textContent);
    const P=JSON.parse(document.getElementById('persist-model').textContent);
    setTimeout(function(){
      R.reached='first timer fired';
      try{
        // State of the clean board BEFORE the import, so "it was already there"
        // cannot be mistaken for "the replay worked".
        const before=MILESTONES.filter(function(x){ return extractSnipId(x.notes)===E.msId; })[0];
        R.refBefore = before?before.ref:null;
        R.rowPresentBefore = E.delRef? TASKS.some(function(t){return t.ref===E.delRef;}) : null;
        R.categories = ANNOT_CATEGORIES.map(function(c){ return c.key+'='+c.count(P); });

        ANNOT_CATEGORIES.forEach(function(c){ c.apply(P); });
        scheduleRerender(true);

        setTimeout(function(){
          try{
            const after=MILESTONES.filter(function(x){ return extractSnipId(x.notes)===E.msId; })[0];
            R.refAfter  = after?after.ref:null;
            R.rowPresentAfter = E.delRef? TASKS.some(function(t){return t.ref===E.delRef;}) : null;
            R.depComment= DEP_COMMENTS[E.depKey]||null;
            R.msComment = MS_COMMENTS[E.msKey]||null;
            // Replaying twice must not double-move or re-delete.
            const n1=MS_MOVES.length;
            ANNOT_CATEGORIES.forEach(function(c){ c.apply(P); });
            const again=MILESTONES.filter(function(x){ return extractSnipId(x.notes)===E.msId; })[0];
            R.refAfterSecond = again?again.ref:null;
            R.movesAdded = MS_MOVES.length-n1;
            R.ok=true;
          }catch(e){ R.err=e.message+' @late'; }
          emit();
        },400);
      }catch(e){ R.err=e.message; emit(); }
    },400);
  }catch(e){ R.err=e.message; emit(); }
})();
"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("No headless Chromium found. Checked: " + ", ".join(CHROME_CANDIDATES))


def render(html: str, budget: int = 30000, b64: bool = True) -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "probe.html"
        tmp.write_text(html, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             f"--virtual-time-budget={budget}", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=300,
        )
    hits = OUT_RE.findall(proc.stdout)
    m = hits[-1] if hits else None
    if m is None:
        sys.exit("Probe output not found; the page likely threw before the probe ran.\n"
                 + proc.stderr[-3000:])
    if b64:
        return json.loads(base64.b64decode(m.strip()).decode("utf-8"))
    raw = (m.replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"'))
    return json.loads(raw)


def inject(html: str, script: str, extras: str = "") -> str:
    out = html.replace("</body>", f"{extras}<script>\n{script}\n</script>\n</body>")
    if out == html:
        sys.exit("Could not find </body> to inject into.")
    return out


def data_block(el_id: str, payload: str) -> str:
    # A script of type application/json is inert markup, not code, so the
    # publish-time script filter and the page's own parser both leave it alone.
    safe = payload.replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<script type="application/json" id="{el_id}">{safe}</script>\n'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    ap.add_argument("--keep", help="directory to write the intermediate files to")
    a = ap.parse_args()

    src = pathlib.Path(a.html)
    html = src.read_text(encoding="utf-8", errors="replace")
    keep = pathlib.Path(a.keep) if a.keep else None
    if keep:
        keep.mkdir(parents=True, exist_ok=True)

    fails, notes = [], []

    # ---------------- stage 1 ----------------
    s1 = render(inject(html, STAGE1), b64=True)
    if not s1.get("ok"):
        print("STAGE 1 FAILED: " + str(s1.get("err")))
        for s in s1.get("steps", []):
            print("   " + s)
        return 1
    for s in s1["steps"]:
        notes.append("stage1  " + s)
    published = s1.pop("publishedText")
    model_text = s1.pop("modelText")
    expect = {k: s1.get(k) for k in
              ("msId", "msKey", "depKey", "fromRef", "toRef", "ovRef", "delRef")}
    if keep:
        (keep / "published.html").write_text(published, encoding="utf-8")
        (keep / "model.json").write_text(model_text, encoding="utf-8")

    model = json.loads(model_text)
    for field in ("dependencyComments", "milestoneMoves", "deletedRows"):
        if field not in model:
            fails.append(f"stage1  export payload is missing {field}")
    if not model.get("dependencyComments", {}).get(expect["depKey"]):
        fails.append("stage1  exported model lost the dependency comment")
    if len(model.get("milestoneMoves", [])) != s1["liveMoves"]:
        fails.append("stage1  exported model did not carry every move")

    # ---------------- stage 2 ----------------
    s2 = render(inject(published, STAGE2, data_block("persist-expect", json.dumps(expect))))
    if not s2.get("ok"):
        fails.append("stage2  probe failed: " + str(s2.get("err")))
    else:
        checks = [
            ("dependency comment", s2["depComment"], "PERSIST dependency note"),
            ("milestone comment", s2["msComment"], "PERSIST comment on a moved milestone"),
            ("milestone health", s2["msHealth"], 2),
            ("short title", s2["msShortTitle"], "PERSIST-SHORT"),
            ("milestone row", s2["msRef"], expect["toRef"]),
            ("row remark", s2["rowRemark"], "PERSIST remark"),
            ("markup count", s2["markupCount"], s1["liveMarkup"]),
            ("move records", s2["moves"], s1["liveMoves"]),
            ("deletion records", s2["deleted"], s1["liveDeleted"]),
        ]
        for name, got, want in checks:
            if got != want:
                fails.append(f"stage2  {name}: got {got!r}, expected {want!r}")
            else:
                notes.append(f"stage2  {name} survived: {got!r}")
        if expect["delRef"] and not s2["delRowGone"]:
            fails.append("stage2  the removed row came back in the published file")
        elif expect["delRef"]:
            notes.append("stage2  removed row stayed removed")
        if not s2.get("headerText"):
            fails.append("stage2  could not read the markup line at all")
        elif "no markup edits yet" in s2["headerText"]:
            fails.append("stage2  markup line still reports no edits: " + s2["headerText"])
        else:
            notes.append("stage2  markup line reports the edits: "
                         + s2["headerText"].split("Markup:")[-1].strip())

    # ---------------- stage 3 ----------------
    s3 = render(inject(html, STAGE3,
                       data_block("persist-expect", json.dumps(expect))
                       + data_block("persist-model", model_text)))
    if not s3.get("ok"):
        fails.append("stage3  probe failed: " + str(s3.get("err")))
    else:
        notes.append("stage3  categories offered: " + ", ".join(s3["categories"]))
        if s3["refBefore"] != expect["fromRef"]:
            fails.append(f"stage3  clean board did not start at {expect['fromRef']!r} "
                         f"(was {s3['refBefore']!r}); the replay proves nothing")
        else:
            notes.append(f"stage3  clean board started at {s3['refBefore']!r}")
        if s3["refAfter"] != expect["toRef"]:
            fails.append(f"stage3  move not replayed: got {s3['refAfter']!r}, "
                         f"expected {expect['toRef']!r}")
        else:
            notes.append(f"stage3  move replayed onto a clean board: "
                         f"{s3['refBefore']!r} -> {s3['refAfter']!r}")
        if expect["delRef"]:
            if not s3["rowPresentBefore"]:
                fails.append("stage3  the row was already absent before the import")
            elif s3["rowPresentAfter"]:
                fails.append("stage3  row removal was not replayed")
            else:
                notes.append("stage3  row removal replayed")
        if s3["depComment"] != "PERSIST dependency note":
            fails.append("stage3  dependency comment not imported")
        else:
            notes.append("stage3  dependency comment imported")
        if s3["refAfterSecond"] != expect["toRef"] or s3["movesAdded"] != 0:
            fails.append(f"stage3  re-import was not idempotent "
                         f"(ref {s3['refAfterSecond']!r}, {s3['movesAdded']} extra moves)")
        else:
            notes.append("stage3  re-importing the same file changed nothing")

    for n in notes:
        print("  ok   " + n)
    for f in fails:
        print("  FAIL " + f)
    print(f"\n{len(notes)} checks passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
