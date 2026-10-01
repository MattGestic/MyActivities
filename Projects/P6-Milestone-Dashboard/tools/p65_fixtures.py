#!/usr/bin/env python3
"""
P65 fixture builder for the notes store (src/modules/notes-store/).

Drives the REAL app headless and makes one of every annotation kind through
the app's own writers, then captures what exportModel() and
publishStatePayload() actually produce:

  * three schedule milestones edited through the milestone card
    (openMsDialog + form + saveMsDialog): health 0 (explicit N/A), health 2
    (done by user, which also fills progress 100), a progress override, a
    finish date and a name override, and a comment on each;
  * a dependency-line comment through saveCommentPanel();
  * a row health and a row remark on a rendered row (the DOM the app's own
    snapshotOverrides() reads);
  * three notes through saveNewNote(), with #ID links, then setNoteStatus()
    to give them three different statuses.

Writes:
  tools/fixtures/p65/model_p64.json      exportModel() output, verbatim
  tools/fixtures/p65/published_p64.json  publishStatePayload() output

The network is unresolvable for the run (--host-resolver-rules), and the probe
is injected with replace("</body>", ...), like every other check here.

Usage: python3 tools/p65_fixtures.py [--html FILE]
"""

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome",
]

PROBE = r"""
(function(){
  const R={ok:false,steps:[],err:null};
  function say(s){ R.steps.push(s); }
  const CAP={}; let capName=null;
  URL.createObjectURL=function(blob){ CAP[capName]=blob; return 'blob:captured'; };
  HTMLAnchorElement.prototype.click=function(){};
  function finish(){
    const out=document.createElement('pre'); out.id='p65-out';
    document.body.appendChild(out);
    out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
  }
  function setVal(id,v){ const e=document.getElementById(id); if(!e) throw new Error('no #'+id); e.value=v; }
  function card(m,edit){
    const id=msId(m);
    const task=TASKS.filter(function(t){ return t.ref===m.ref; })[0]||{name:'',disc:'',ref:m.ref,hrs:'',type:'Weighted'};
    openMsDialog(m,id,document.body,computeHours(task),task);
    if(msDraftClean==null) msDraftClean=msReadForm();
    edit();
    saveMsDialog(true);
    say('card saved on '+id+' key '+msKeyFor(m));
  }
  function addDays(iso,n){ const d=new Date(iso+'T00:00:00'); d.setDate(d.getDate()+n); return isoDay(d); }
  function healthDot(v){ return document.querySelector('#ms-health-dots .health-dot[data-val="'+v+'"]'); }
  setTimeout(function(){
   try{
    window.confirm=function(){ return true; };
    const cand=MILESTONES.filter(function(m){ return msId(m)&&!/^USR-/.test(msId(m))&&m.date&&!m.actual; });
    if(cand.length<3) throw new Error('fewer than 3 editable milestones');
    const a=cand[0], b=cand[1], c=cand[2];
    R.keys=[msKeyFor(a),msKeyFor(b),msKeyFor(c)];
    // A: explicit N/A (health 0), a comment, and a name override.
    card(a,function(){
      onMsHealthClick(healthDot(0));
      setVal('ms-title','P65 renamed milestone A');
      setVal('ms-comment-text','P65 comment A, health N/A');
    });
    // B: done by user (health 2 fills progress 100 when the schedule is not 100), a comment.
    card(b,function(){
      onMsHealthClick(healthDot(2));
      setVal('ms-comment-text','P65 comment B, marked done');
    });
    // C: a progress override, a finish date move, a start date move, a comment.
    const cProg=(c.progress===37)?73:37;
    card(c,function(){
      setVal('ms-progress-input',String(cProg));
      setVal('ms-date',addDays(c.date,7));
      if(c.start) setVal('ms-start-date',addDays(c.start,-7));
      setVal('ms-comment-text','P65 comment C, progress and dates');
    });
    // Dependency-line comment through the panel's own save.
    const depKey=edgeKey('pred',msId(a),msId(b));
    activeCommentKeys=[depKey];
    document.getElementById('dep-comment-text').value='P65 dependency comment';
    saveCommentPanel();
    say('dep comment '+depKey);
    // Three notes with links, then three statuses.
    [['P65 note one about #'+msId(a),null],
     ['P65 note two about #'+msId(b)+' and #'+msId(c),'sent'],
     ['P65 note three, general','done']].forEach(function(pair){
      document.getElementById('note-input').value=pair[0];
      saveNewNote();
      const n=NOTES[NOTES.length-1];
      if(pair[1]) setNoteStatus(n.nid,pair[1]);
      say('note '+n.nid+' '+n.status);
    });
    NOTE_COLLECTIONS[reportPeriodISO()]={title:'P65 collection',to:'Reviewer'};
    setTimeout(function(){
     try{
      // Row health and a row remark, on the rendered row snapshotOverrides() reads.
      const tr=document.querySelector('tr[data-type="row"]');
      R.rowRef=tr.getAttribute('data-ref');
      const dot=tr.querySelector('.health-dot');
      const orig=dot.getAttribute('data-orig-health');
      dot.setAttribute('data-current-health',String(orig)==='3'?'1':'3');
      tr.querySelector('.remarks').textContent='P65 row remark';
      say('row override on '+R.rowRef);
      capName='model'; exportModel();
      R.published=publishStatePayload();
      CAP.model.text().then(function(t){ R.model=JSON.parse(t); R.ok=true; finish(); },
                            function(e){ R.err='capture '+e.message; finish(); });
     }catch(e){ R.err=e.message+' @inner'; finish(); }
    },400);
   }catch(e){ R.err=e.message+' @outer '+e.stack; finish(); }
  },600);
})();
"""


def find_chrome():
    # P74 (TD-239): every launch goes through tools/check_map/chrome_fixture.py,
    # which seeds the reference baseline into the current app (the app ships
    # with none) and hands on to $SRET_CHROME (tools/run_checks.py coverage
    # capture) when set, else to the real Chromium.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "check_map"))
    import chrome_fixture
    return chrome_fixture.launcher()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html).read_text(encoding="utf-8")
    injected = html.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>", 1)
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p65_probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             "--virtual-time-budget=20000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=240)
    m = re.search(r'<pre id="p65-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    for s in R.get("steps", []):
        print("  " + s)
    if not R.get("ok"):
        sys.exit("Probe failed: " + str(R.get("err")))
    out = HERE / "fixtures" / "p65"
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_p64.json").write_text(json.dumps(R["model"], indent=1), encoding="utf-8")
    (out / "published_p64.json").write_text(json.dumps(R["published"], indent=1), encoding="utf-8")
    print("wrote", out / "model_p64.json")
    print("wrote", out / "published_p64.json")


if __name__ == "__main__":
    main()
