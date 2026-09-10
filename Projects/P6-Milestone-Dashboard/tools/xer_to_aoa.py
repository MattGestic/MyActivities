#!/usr/bin/env python3
"""
Primavera XER extractor for the P6 Milestone Dashboard.

Reads a P6 .xer export and emits the same array-of-arrays shape the app's
.xlsx path produces, so an XER can be run through the real ingest pipeline
without the app itself yet understanding the format.

Why this exists now: XER ingest is a wanted future feature, and until it is
built this converter is the only way to exercise the row model against a real
EPCM schedule. It is deliberately a standalone tool, not app code.

XER structure: a flat text file of tab-delimited table blocks. %T names a
table, %F names its fields, %R is a record. Encoding is cp1252 in practice,
not UTF-8.

Mapping to the columns the app expects:
  Activity ID          TASK.task_code, indented by WBS depth so the app's
                       existing indent-based hierarchy detection works
  Activity Name        TASK.task_name
  Duration             TASK.target_drtn_hr_cnt converted to days
  Start / Finish       actual dates when present (suffixed " A", matching the
                       P6 print convention the app already parses), otherwise
                       the early dates
  Predecessor Details  built from TASKPRED as "CODE: FS 2", the same shape the
                       xlsx export uses
  Successor Details    the same relationships inverted
  Total Float          TASK.total_float_hr_cnt converted to days

Assumption worth knowing: hour-to-day conversion uses an 8 hour day. XER
stores durations and float in hours; the xlsx export states them in days.
Pass --hours-per-day to change it.

Usage:
  python3 tools/xer_to_aoa.py FILE.xer [--json OUT] [--csv OUT] [--hours-per-day 8]
"""

import argparse
import collections
import csv
import json
import pathlib
import sys

REL = {"PR_FS": "FS", "PR_SS": "SS", "PR_FF": "FF", "PR_SF": "SF"}


def read_tables(path: pathlib.Path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        sys.exit("Could not decode the XER with any known encoding.")

    tables, name, fields = {}, None, []
    for line in txt.splitlines():
        if line.startswith("%T"):
            name = line.split("\t")[1].strip()
            tables[name] = []
            fields = []
        elif line.startswith("%F") and name:
            fields = [f.strip() for f in line.split("\t")[1:]]
        elif line.startswith("%R") and name:
            vals = line.split("\t")[1:]
            tables[name].append(dict(zip(fields, vals)))
    return tables


def wbs_paths(projwbs):
    """wbs_id -> list of names from root to that node."""
    by_id = {w["wbs_id"]: w for w in projwbs}
    cache = {}

    def path(wid, guard=0):
        if wid in cache:
            return cache[wid]
        node = by_id.get(wid)
        if not node or guard > 60:
            return []
        parent = node.get("parent_wbs_id") or ""
        out = (path(parent, guard + 1) if parent in by_id else []) + [node.get("wbs_name", "").strip()]
        cache[wid] = out
        return out

    return {w: path(w) for w in by_id}


def to_days(hours, hpd):
    try:
        return round(float(hours) / hpd, 1) if hours not in ("", None) else ""
    except (TypeError, ValueError):
        return ""


def fmt_date(value, actual):
    """XER stores 'YYYY-MM-DD HH:MM'. Keep the date and the P6 actual suffix."""
    if not value:
        return ""
    d = value.split(" ")[0]
    return d + (" A" if actual else "")


def build(path: pathlib.Path, hpd: float):
    t = read_tables(path)
    tasks = t.get("TASK", [])
    preds = t.get("TASKPRED", [])
    paths = wbs_paths(t.get("PROJWBS", []))

    code = {x["task_id"]: x.get("task_code", "") for x in tasks}

    pred_of = collections.defaultdict(list)
    succ_of = collections.defaultdict(list)
    for p in preds:
        tid, pid = p.get("task_id"), p.get("pred_task_id")
        rel = REL.get(p.get("pred_type", ""), p.get("pred_type", "").replace("PR_", ""))
        lag = to_days(p.get("lag_hr_cnt"), hpd)
        lag_txt = f" {int(float(lag))}" if lag not in ("", 0, 0.0) else ""
        if tid in code and pid in code:
            pred_of[tid].append(f"{code[pid]}: {rel}{lag_txt}")
            succ_of[pid].append(f"{code[tid]}: {rel}{lag_txt}")

    # Group activities under their WBS node, then emit heading rows followed by
    # their activities, indented, exactly as the xlsx export is laid out.
    by_wbs = collections.defaultdict(list)
    for x in tasks:
        by_wbs[x.get("wbs_id", "")].append(x)

    header = ["Activity ID", "Activity Name", "Duration", "Start", "Finish",
              "Predecessor Details", "Successor Details", "Total Float"]
    aoa = [header]
    emitted_headings = set()

    for wid in sorted(by_wbs, key=lambda w: [s.lower() for s in paths.get(w, [])]):
        parts = paths.get(wid, [])
        for depth in range(len(parts)):
            key = tuple(parts[: depth + 1])
            if key in emitted_headings:
                continue
            emitted_headings.add(key)
            aoa.append(["  " * depth + parts[depth], "", "", "", "", "", "", ""])
        depth = len(parts)
        for x in sorted(by_wbs[wid], key=lambda r: r.get("task_code", "")):
            tid = x["task_id"]
            act_s, act_e = x.get("act_start_date", ""), x.get("act_end_date", "")
            start = fmt_date(act_s or x.get("early_start_date") or x.get("target_start_date"), bool(act_s))
            finish = fmt_date(act_e or x.get("early_end_date") or x.get("target_end_date"), bool(act_e))
            aoa.append([
                "  " * depth + x.get("task_code", ""),
                x.get("task_name", ""),
                to_days(x.get("target_drtn_hr_cnt"), hpd),
                start, finish,
                ", ".join(pred_of.get(tid, [])),
                ", ".join(succ_of.get(tid, [])),
                to_days(x.get("total_float_hr_cnt"), hpd),
            ])
    return aoa, {"tasks": len(tasks), "links": len(preds), "wbs": len(paths),
                 "headings": len(emitted_headings)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xer")
    ap.add_argument("--json")
    ap.add_argument("--csv")
    ap.add_argument("--hours-per-day", type=float, default=8.0)
    a = ap.parse_args()

    aoa, stats = build(pathlib.Path(a.xer), a.hours_per_day)
    print(f"TASK {stats['tasks']}   TASKPRED {stats['links']}   "
          f"PROJWBS {stats['wbs']}   headings emitted {stats['headings']}")
    print(f"AoA rows {len(aoa)} (1 header + {stats['headings']} headings + "
          f"{len(aoa) - 1 - stats['headings']} activities)")
    print("\nSample activity rows:")
    shown = 0
    for r in aoa[1:]:
        if r[1] and shown < 4:
            print("   " + " | ".join(str(c)[:34] for c in r[:7]))
            shown += 1

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(aoa), encoding="utf-8")
        print(f"\nJSON written to {a.json}")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh, lineterminator="\n").writerows(aoa)
        print(f"CSV written to {a.csv}")


if __name__ == "__main__":
    main()
