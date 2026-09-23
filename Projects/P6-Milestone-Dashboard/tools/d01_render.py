#!/usr/bin/env python3
"""
D-01 render builder: static design mockups (RENDERS, not the live app) for the
milestone card and two related surfaces (import review, saved-lists panel).

WHAT THIS DOES NOT DO
----------------------
It never touches src/milestone-dashboard.html. Every token and every rule this
script uses for the P45 baseline (card layout, dirty-field tint, saved marks,
button classes, colour tokens) is COPIED from that file as a string constant
below, with the line range it was copied from noted next to it, so a reviewer
can diff this script's constants against the app instead of trusting a
paraphrase. New states 1-11 (card + import review) are built as plain static
HTML/CSS using only tokens defined below (all copied from the app). States 12
and 13 (the saved-lists panel) are a STATIC MOCK of the board, not the real
app loaded in Chromium: the real board is an 11k-line generated table with a
dependency-line SVG overlay, and reproducing enough of it faithfully inside a
render script would risk misrepresenting the very thing under review. The
mock board rows use the app's real phase-band and status colour tokens so the
docked panel itself renders faithfully; only the rows behind it are a
simplification, and the review page says so on those two frames.

Usage:
  python3 tools/d01_render.py
Writes docs/mockups/D-01/png/*.png and (re)writes
docs/mockups/D-01/render_review.html.
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "mockups" / "D-01"
PNG_DIR = OUT_DIR / "png"
APP_HTML = ROOT / "src" / "milestone-dashboard.html"

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    raise SystemExit("No headless Chromium found in " + str(CHROME_CANDIDATES))


# ---------------------------------------------------------------------------
# TOKENS — copied verbatim from milestone-dashboard.html, light block lines
# 9-116, dark block lines 117-203, non-themed :root block lines 204-345
# (font-sans/mono, space-*, text-*, radius-*). Two custom properties in the
# app's own :root block are self-referential (--color-shadow-dialog-near/far
# at app lines 260-261, defined as var(--color-shadow-dialog-near) / (...-far)
# — they never resolve to a real value anywhere in the app either). This
# script uses the app's --color-shadow-soft (a real, defined token) for both
# dialog shadow layers instead. That is the one token substitution in this
# whole render; every other value below is copied unchanged.
# ---------------------------------------------------------------------------

TOKENS_LIGHT = """
html[data-theme="light"]{
  --color-bg-header:#2e4f82; --color-bg-panel:#f4f5f8; --color-bg-subtle:#f4f5f8;
  --color-bg-canvas:#fdfdfc; --color-bg-elevated:#ffffff; --color-row-selected:#f0ecf9;
  --color-dialog-bg:rgba(253,253,252,0.92); --color-dialog-elev:#ffffff;
  --color-border-panel:#e3e2de; --color-line-hairline:#eeede9; --color-line-default:#e3e2de;
  --color-text-primary:#17191c; --color-text-ink:#17191c; --color-text-muted:#6f7480;
  --color-text-label:#8a8f99; --color-text-mono:#848994; --color-text-on-panel:#17191c;
  --color-text-on-panel-muted:#575c67; --color-text-emphasis:#2e4f82; --color-text-small:#4c515c;
  --color-text-faint:#8a8f99; --color-text-note:#767b85;
  --color-status-track:#2f6fed; --color-status-risk:#a2690a; --color-status-risk-fill:#b8770c;
  --color-status-done:#1f9d55; --color-status-crit:#c0392b; --color-status-future:#b9bdc4;
  --color-status-track-bg:#e6e5e1; --color-crit:#c0392b;
  --color-accent-purple:#8b64c7; --color-purple-dark:#6f4fa3; --color-purple-deep:#8b64c7;
  --color-btn-active-bg:#17191c; --color-btn-active-text:#fdfdfc; --color-btn-inactive-bg:#ffffff;
  --color-btn-inactive-border:#e3e2de; --color-btn-inactive-text:#6f7480; --color-btn-hover-bg:#f4f5f8;
  --color-comment-indicator:#8b64c7;
  --color-filter-bg:#e4e9ed; --color-filter-border:#c9d2d8;
  --color-text-on-accent:#ffffff; --color-accent-tint-bg:#efe6f9; --color-crit-tint-bg:#fdecec;
  --color-badge-neutral-bg:#889; --color-label-neutral-bg:#e8eaf2; --color-row-alt-bg:#fafbfc;
  --color-row-gate-bg:#eef0fa; --color-row-alt-muted-bg:#f2f2f6; --color-col-past-bg:#e6e6e6;
  --color-col-filtered-bg:#e0c8f6; --color-row-hover-bg:#f0f4ff; --color-subtotal-accent:#a2690a;
  --color-col-filtered-alt-bg:#d4b8ed; --color-ready-tint-bg:#e8f2ec; --color-crit-text:#7a1a1a;
  --color-ok-text:#1a6b3a; --color-accent-ink:#6f46ad; --color-input-border:#b8c0d8;
  --color-row-default-bg:#ffffff; --color-vt-divider:#b8c0d8;
  --color-btn-outline:#9fb0bd; --color-btn-primary-bg:#1c3a63; --color-btn-primary-text:#ffffff;
  --color-btn-primary-outline:#1c3a63; --color-btn-primary-hover-bg:#2a4a7a;
  --color-btn-primary-pressed-bg:#14294a; --color-btn-secondary-bg:#ffffff;
  --color-btn-secondary-text:#1c3a63; --color-btn-secondary-outline:#9fb0bd;
  --color-btn-secondary-hover-bg:#eef1f7; --color-btn-secondary-pressed-bg:#dde6f5;
  --color-btn-icon-hover-bg:#dde1ea; --color-btn-icon-pressed-bg:#ccd2de;
  --color-shadow-soft:rgba(0,0,0,.18); --color-scrim:rgba(10,12,30,.35);
  --color-crit-border:#800;
}
"""

TOKENS_DARK = """
html[data-theme="dark"]{
  --color-bg-header:#15182F; --color-bg-panel:#1e2240; --color-bg-subtle:#232f4a;
  --color-bg-canvas:#1c2942; --color-bg-elevated:#232f4a; --color-row-selected:#2a2d5a;
  --color-dialog-bg:rgba(28,41,66,0.92); --color-dialog-elev:#232f4a;
  --color-border-panel:rgba(160,184,230,.2); --color-line-hairline:rgba(160,184,230,.14);
  --color-line-default:rgba(160,184,230,.2);
  --color-text-primary:#e8eef8; --color-text-ink:#e8eef8; --color-text-muted:#8b9bb8;
  --color-text-label:#8b9bb8; --color-text-mono:#b7c6e0; --color-text-on-panel:#cde;
  --color-text-on-panel-muted:#8ab; --color-text-emphasis:#c4d2e8; --color-text-small:#334;
  --color-text-faint:#556; --color-text-note:#889;
  --color-status-track:#1355c4; --color-status-risk:#c07500; --color-status-risk-fill:#c07500;
  --color-status-done:#1f9d55; --color-status-crit:#c00000; --color-status-future:#c8c8c8;
  --color-status-track-bg:#24324d; --color-crit:#c00000;
  --color-accent-purple:#8b64c7; --color-purple-dark:#4a2f7a; --color-purple-deep:#5a3a8e;
  --color-btn-active-bg:#8b64c7; --color-btn-active-text:#fff; --color-btn-inactive-bg:#1e2240;
  --color-btn-inactive-border:rgba(160,184,230,.2); --color-btn-inactive-text:#b7c6e0;
  --color-btn-hover-bg:#2a2e50; --color-comment-indicator:#8b64c7;
  --color-filter-bg:#1e2240; --color-filter-border:rgba(160,184,230,.2);
  --color-text-on-accent:#ffffff; --color-accent-tint-bg:#2a2440; --color-crit-tint-bg:#3a1a1a;
  --color-badge-neutral-bg:#5a6478; --color-label-neutral-bg:#2a2e50; --color-row-alt-bg:#202a45;
  --color-row-gate-bg:#20264a; --color-row-alt-muted-bg:#232748; --color-col-past-bg:#2a2d38;
  --color-col-filtered-bg:#5a3a8e; --color-row-hover-bg:#2a2d5a; --color-subtotal-accent:#e8d050;
  --color-col-filtered-alt-bg:#3a2d5c; --color-ready-tint-bg:#1a3324; --color-crit-text:#e88888;
  --color-ok-text:#7fd6a0; --color-accent-ink:#a98ad8; --color-input-border:#3a3e60;
  --color-row-default-bg:#262931; --color-vt-divider:#4a5580;
  --color-btn-outline:#3a3e60; --color-btn-primary-bg:#3a6ea8; --color-btn-primary-text:#ffffff;
  --color-btn-primary-outline:#3a6ea8; --color-btn-primary-hover-bg:#4a80ba;
  --color-btn-primary-pressed-bg:#2a5a8e; --color-btn-secondary-bg:#1e2240;
  --color-btn-secondary-text:#9cbcff; --color-btn-secondary-outline:#3a3e60;
  --color-btn-secondary-hover-bg:#2a2e50; --color-btn-secondary-pressed-bg:#343a5e;
  --color-btn-icon-hover-bg:#2a2e50; --color-btn-icon-pressed-bg:#141830;
  --color-shadow-soft:rgba(0,0,0,.4); --color-scrim:rgba(10,12,30,.5);
  --color-crit-border:#800;
}
"""

TOKENS_ROOT = """
:root{
  --color-band-1:#5B6472; --color-band-2:#4154A6; --color-band-3:#1D9E75;
  --color-band-4:#B56500; --color-band-5:#A00000; --color-band-divider:rgba(255,255,255,.2);
  --color-accent-wash-weak:rgba(139,100,199,.05); --color-accent-wash:rgba(139,100,199,.10);
  --color-accent-wash-strong:rgba(139,100,199,.6);
  --color-health-none-fill:#fff; --color-health-none-border:#bbb; --color-health-good:#158a28;
  --color-health-good-border:#0e6a1c; --color-health-watch:#e8b520; --color-health-watch-border:#a0800f;
  --color-health-info:#2e6fd9; --color-health-info-border:#1e4f9c; --color-health-rim:rgba(0,0,0,.15);
  --font-sans:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,monospace;
  --space-0:0; --space-1:2px; --space-2:4px; --space-3:6px; --space-4:8px; --space-5:12px;
  --space-6:16px; --space-7:24px;
  --text-xs:9px; --text-sm:10px; --text-base:11px; --text-md:12px; --text-lg:14px;
  --radius-sm:4px; --radius-md:6px; --radius-pill:999px;
  --color-icon-done:var(--color-text-ink); --color-icon-doneuser:var(--color-status-done);
  --color-icon-track:var(--color-status-track); --color-icon-risk:var(--color-status-risk-fill);
  --color-icon-crit:var(--color-status-crit); --color-icon-future:var(--color-status-future);
}
"""

# ---------------------------------------------------------------------------
# CARD CSS — copied verbatim from milestone-dashboard.html lines 1506-1692
# (the .ms-dialog block), including its own comments, so it is a real diff
# target. --color-shadow-dialog-near/-far substituted for --color-shadow-soft
# per the note above (the app's own tokens do not resolve).
# ---------------------------------------------------------------------------
CARD_CSS = """
.ms-dialog{position:relative;box-sizing:border-box;width:306px;
  padding:14px 16px 13px;background:var(--color-dialog-bg);color:var(--color-text-ink);
  border:1px solid var(--color-line-default);border-radius:12px;
  box-shadow:0 1px 2px var(--color-shadow-soft),0 8px 24px var(--color-shadow-soft);
  font-family:var(--font-sans)}
.ms-dialog *,.ms-dialog *::before,.ms-dialog *::after{box-sizing:border-box}
.ms-dialog-head{display:flex;align-items:center;gap:var(--space-3);min-height:19px}
.ms-heading{display:flex;align-items:center;gap:var(--space-3);min-width:0}
.ms-heading .ms-code{white-space:nowrap}
.ms-heading .ms-status{white-space:nowrap;margin-left:auto}
.ms-head-spacer{flex:1 1 auto;min-width:0}
.ms-close{background:none;border:none;font-size:13px;line-height:1;color:var(--color-text-muted);cursor:pointer;padding:3px;border-radius:4px;margin:-3px 0 0 -3px}
.ms-close:hover{color:var(--color-status-crit);background:var(--color-btn-hover-bg)}
.ms-icon-btn{display:inline-flex;align-items:center;justify-content:center;
  width:19px;height:19px;padding:0;border:1px solid transparent;border-radius:5px;
  background:none;cursor:pointer;transition:background .12s,border-color .12s;flex:0 0 auto}
.ms-icon-btn:hover{background:var(--color-accent-wash-weak);border-color:var(--color-accent-purple)}
.ms-edited-mark{display:inline-block;width:5px;height:5px;margin-left:4px;border-radius:99px;
  background:var(--color-accent-purple);vertical-align:middle;cursor:help;flex:0 0 auto}
.ms-edited-mark[hidden]{display:none}
.ms-save-actions{display:inline-flex;align-items:center;gap:var(--space-2);flex:0 0 auto}
.ms-save-actions[hidden]{display:none}
.ms-act{font:650 10px var(--font-sans);padding:3px 7px;border-radius:5px;
  border:1px solid var(--color-accent-purple);background:var(--color-accent-purple);
  color:var(--color-text-on-accent);cursor:pointer;white-space:nowrap}
.ms-act:hover{filter:brightness(1.08)}
.ms-code{font:700 12px/1 var(--font-mono);color:var(--color-text-mono)}
.ms-status{font:600 11px/1 var(--font-sans)}
.ms-dialog.status-track .ms-status{color:var(--color-status-track)}
.ms-dialog.status-risk .ms-status{color:var(--color-status-risk)}
.ms-title{margin:0;font-weight:600;font-size:14.5px;line-height:1.28;letter-spacing:-.01em}
.ms-sub{margin:var(--space-2) 0 2px;font:450 11px var(--font-sans);color:var(--color-text-muted)}
.ms-title-row{display:flex;gap:10px;align-items:stretch}
.ms-title-col{flex:1 1 auto;min-width:0}
.ms-float-col{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;padding:1px 2px 1px 9px;
  border-left:1px solid var(--color-line-hairline)}
.ms-float-val{font-weight:600;font-size:13px;line-height:1.3;white-space:nowrap;
  font-variant-numeric:tabular-nums;color:var(--color-text-primary)}
.ms-float-lbl{font-size:11px;line-height:1.3;color:var(--color-text-muted);font-style:italic}
.ms-schedule{margin-top:12px;padding-top:10px;border-top:1px solid var(--color-line-hairline);
  display:grid;grid-template-columns:1fr 1fr 1fr;align-items:stretch;gap:10px}
.ms-schedule .ms-field{display:flex;flex-direction:column;justify-content:flex-end;min-width:0}
.ms-prog-field{align-items:flex-end;padding-left:10px;border-left:1px solid var(--color-line-hairline)}
.ms-lbl{display:block;margin-bottom:4px;font:500 10px var(--font-sans);letter-spacing:.08em;text-transform:uppercase;color:var(--color-text-label)}
.ms-date,.ms-prog-input{font-weight:600;font-size:14px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.ms-title,.ms-date,.ms-float-val,.ms-val-input{
  border:none;background:transparent;color:inherit;font-family:inherit;
  border-radius:3px;transition:background .12s;width:100%;min-width:0}
.ms-title:hover,.ms-date:hover,.ms-float-val:hover,.ms-val-input:hover{background:var(--color-accent-wash-weak)}
.ms-title:focus,.ms-date:focus,.ms-float-val:focus,.ms-val-input:focus{
  background:var(--color-accent-wash);color:var(--color-accent-ink);outline:2px solid var(--color-accent-purple);outline-offset:1px}
.ms-dirty-field{background:var(--color-accent-wash);color:var(--color-accent-ink)}
.ms-title{padding:0;margin:0;display:block}
.ms-date{padding:0 var(--space-1);margin-left:-2px}
.ms-progress-track{margin-top:11px;height:3px;border-radius:99px;background:var(--color-status-track-bg);overflow:hidden}
.ms-progress-fill{height:100%;border-radius:inherit;background:var(--color-status-track)}
.ms-comment-block{margin-top:11px;padding-top:10px;border-top:1px solid var(--color-line-hairline)}
.ms-comment-head{display:flex;align-items:center;gap:var(--space-3);margin-bottom:5px}
.ms-head-divider{width:1px;align-self:stretch;background:var(--color-line-default)}
.ms-health-dots{display:flex;gap:var(--space-2);align-items:center;margin-left:auto}
.ms-health-dots .health-dot{width:13px;height:13px;cursor:pointer;border:1.2px solid var(--color-health-rim)}
.health-dot.mh-0{background:var(--color-health-none-fill)}
.health-dot.mh-2{background:var(--color-health-good);border-color:var(--color-health-good-border)}
.health-dot.mh-3{background:var(--color-health-watch);border-color:var(--color-health-watch-border)}
.toggle-btn{font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid var(--color-btn-secondary-outline);background:var(--color-btn-secondary-bg);cursor:pointer;color:var(--color-btn-secondary-text)}
.toggle-btn.active{background:var(--color-btn-primary-bg);color:var(--color-btn-primary-text);border-color:var(--color-btn-primary-outline)}
"""

# ---------------------------------------------------------------------------
# NEW component CSS for D-01. Every colour is one of the tokens above; none
# invented. Roles borrowed where a dedicated one does not exist are called
# out inline and repeated in the final report.
# ---------------------------------------------------------------------------
NEW_CSS = """
body{margin:0;background:var(--color-bg-canvas);font-family:var(--font-sans);color:var(--color-text-ink)}
.frame-pad{padding:28px;display:inline-block}
/* Per-field discard control (NEW). Borrows .icon-btn's icon-button family
   (width/height/radius) and the --color-btn-icon-* hover/press tokens,
   since there is no dedicated "inline field icon button" role yet. */
.field-row{display:flex;align-items:center;gap:2px}
.field-x{display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;min-width:12px;min-height:12px;border-radius:4px;border:none;
  background:transparent;color:var(--color-text-muted);cursor:pointer;font-size:11px;line-height:1;
  flex:0 0 auto}
.field-x:hover{background:var(--color-btn-icon-hover-bg);color:var(--color-status-crit)}
.field-x:active{background:var(--color-btn-icon-pressed-bg)}
/* Saved mark (NEW), replacing the P44 purple dot with a superscript asterisk
   in the same accent-ink token the dirty tint already uses for "changed". */
.saved-mark{color:var(--color-accent-ink);font-weight:700;font-size:12px;
  vertical-align:super;line-height:0;margin-left:1px;cursor:help}
/* Schedule-changed glyph (NEW). Same icon-button family as .ms-icon-btn but
   coloured with --color-status-risk, the app's existing "needs attention"
   role, since a changed-pending-review state is closer to risk than to the
   plain accent used for edits. */
.sched-changed{display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;border-radius:4px;background:none;border:none;cursor:help;
  color:var(--color-status-risk);font-size:12px;margin-left:2px}
.sched-changed:hover{background:var(--color-accent-wash-weak)}
/* NEW badge pill. Reuses the accent-wash / accent-ink pairing .ms-type-opt.active
   already uses for "this is the active/called-out one" rather than inventing a
   badge-specific colour. */
.new-badge{display:inline-block;padding:1px 6px;border-radius:var(--radius-pill);
  background:var(--color-accent-wash);color:var(--color-accent-ink);
  font:700 9px var(--font-sans);letter-spacing:.04em;text-transform:uppercase;margin-left:6px}
.remap{font:500 11px var(--font-mono);color:var(--color-text-muted);margin-left:6px}
/* Tooltip bubble, shown open for the demo frames (native title tooltips do
   not render in a screenshot). Same dialog-elevation treatment as the card
   itself. */
.demo-tip{position:absolute;z-index:5;max-width:190px;padding:6px 8px;border-radius:6px;
  background:var(--color-dialog-elev);border:1px solid var(--color-line-default);
  box-shadow:0 4px 14px var(--color-shadow-soft);font-size:10px;line-height:1.4;
  color:var(--color-text-ink)}
.demo-tip .tip-line2{color:var(--color-text-muted)}

/* Comment thread (NEW), replacing the single textarea. */
.thread-head{display:flex;align-items:center;gap:var(--space-3);margin-bottom:6px}
.thread-title{font:600 11px var(--font-sans);color:var(--color-text-ink)}
.thread-clear{margin-left:auto;background:none;border:none;color:var(--color-text-muted);
  font:500 10px var(--font-sans);cursor:pointer;text-decoration:underline;padding:0}
.thread-clear:hover{color:var(--color-status-crit)}
.thread-add{width:100%;padding:6px 8px;border-radius:6px;border:1px solid var(--color-line-default);
  background:var(--color-bg-elevated);color:var(--color-text-ink);font:450 10.5px var(--font-sans);
  margin-bottom:8px}
.thread-entry{padding:6px 0;border-top:1px solid var(--color-line-hairline)}
.thread-entry:first-child{border-top:none}
.thread-body{font:450 10.5px/1.4 var(--font-sans);color:var(--color-text-ink);margin:0 0 3px}
.thread-meta{display:flex;align-items:center;gap:6px}
.thread-time{font:450 9px var(--font-sans);color:var(--color-text-muted)}
.thread-pill{font:600 8.5px var(--font-sans);padding:1px 6px;border-radius:var(--radius-pill);
  background:var(--color-label-neutral-bg);color:var(--color-text-on-panel-muted)}
.thread-entry.prior .thread-body,.thread-entry.prior .thread-time{color:var(--color-text-muted)}
.thread-entry.prior .thread-pill{background:var(--color-row-alt-muted-bg)}
.thread-more{display:block;margin-top:4px;background:none;border:none;color:var(--color-accent-ink);
  font:500 10px var(--font-sans);cursor:pointer;padding:0;text-decoration:underline}
/* Clear confirmation (NEW). Danger action styled with the app's existing
   crit tokens (--color-crit-tint-bg / --color-crit-text), since there is no
   separate "danger button" role defined anywhere in the app yet. */
.clear-confirm{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;
  background:var(--color-crit-tint-bg)}
.clear-confirm span{font:500 10.5px var(--font-sans);color:var(--color-crit-text);flex:1 1 auto}
.btn-danger{font:650 10px var(--font-sans);padding:3px 9px;border-radius:5px;
  border:1px solid var(--color-status-crit);background:var(--color-status-crit);
  color:var(--color-text-on-accent);cursor:pointer}
.btn-cancel{font:500 10px var(--font-sans);padding:3px 9px;border-radius:5px;
  border:1px solid var(--color-btn-secondary-outline);background:var(--color-btn-secondary-bg);
  color:var(--color-btn-secondary-text);cursor:pointer}

/* Phone bottom sheet (state 09). */
.sheet-wrap{width:390px;height:100%;background:var(--color-bg-canvas);position:relative}
.sheet{position:absolute;bottom:0;left:0;right:0;background:var(--color-dialog-elev);
  border-radius:16px 16px 0 0;box-shadow:0 -4px 20px var(--color-shadow-soft);
  padding:8px 16px 0}
.sheet .ms-dialog{width:100%;border:none;box-shadow:none;border-radius:0;padding:0 0 76px;background:transparent}
.drag-handle{width:36px;height:4px;border-radius:99px;background:var(--color-line-default);margin:0 auto 10px}
.sheet-savebar{position:absolute;left:0;right:0;bottom:0;padding:10px 16px;
  background:var(--color-dialog-elev);border-top:1px solid var(--color-line-default);
  display:flex;justify-content:flex-end;gap:8px}

/* Import review dialog (states 10-11). */
.imp-dialog{width:520px;background:var(--color-dialog-elev);border:1px solid var(--color-line-default);
  border-radius:12px;box-shadow:0 8px 24px var(--color-shadow-soft);font-family:var(--font-sans);
  color:var(--color-text-ink)}
.imp-head{padding:14px 18px;border-bottom:1px solid var(--color-line-default)}
.imp-title{margin:0;font:600 13px var(--font-sans)}
.imp-rows{padding:6px 0}
.imp-row{display:flex;align-items:center;gap:10px;padding:9px 18px;border-bottom:1px solid var(--color-line-hairline);cursor:pointer}
.imp-row:hover{background:var(--color-btn-hover-bg)}
.imp-row.conflict{background:var(--color-crit-tint-bg)}
.imp-row.conflict:hover{background:var(--color-crit-tint-bg)}
.imp-cat{flex:1 1 auto;font:500 11px var(--font-sans)}
.imp-count{font:700 11px var(--font-mono);color:var(--color-text-mono);min-width:22px;text-align:right}
.imp-action{font:600 10px var(--font-sans);color:var(--color-text-muted);min-width:120px;text-align:right}
.imp-row.conflict .imp-action{color:var(--color-crit-text);font-weight:700}
.imp-chev{color:var(--color-text-label);font-size:11px}
.imp-foot{display:flex;align-items:center;gap:10px;padding:12px 18px;border-top:1px solid var(--color-line-default)}
.imp-note{font:500 9.5px var(--font-sans);color:var(--color-crit-text);margin-right:auto}
.imp-primary{font:650 10.5px var(--font-sans);padding:5px 12px;border-radius:6px;border:1px solid var(--color-accent-purple);
  background:var(--color-accent-purple);color:var(--color-text-on-accent);cursor:pointer}
.imp-secondary{font:500 10.5px var(--font-sans);padding:5px 12px;border-radius:6px;
  border:1px solid var(--color-btn-secondary-outline);background:var(--color-btn-secondary-bg);
  color:var(--color-btn-secondary-text);cursor:pointer}
.imp-selbar{display:flex;align-items:center;gap:8px;padding:8px 18px;background:var(--color-accent-wash);
  font:500 10.5px var(--font-sans);color:var(--color-accent-ink)}
.imp-selbar select{font:500 10px var(--font-sans);padding:2px 6px;border-radius:5px;
  border:1px solid var(--color-input-border);background:var(--color-bg-elevated);color:var(--color-text-ink)}
.imp-selbar .imp-primary{margin-left:auto;padding:3px 10px}
table.imp-table{width:100%;border-collapse:collapse;font-size:10.5px}
table.imp-table th{text-align:left;font:600 9px var(--font-sans);text-transform:uppercase;
  letter-spacing:.04em;color:var(--color-text-label);padding:6px 18px;border-bottom:1px solid var(--color-line-default)}
table.imp-table td{padding:6px 18px;border-bottom:1px solid var(--color-line-hairline);color:var(--color-text-ink)}
table.imp-table tr.ticked{background:var(--color-accent-wash-weak)}
.imp-was-now{color:var(--color-text-muted)}
.imp-default{color:var(--color-text-muted);font-size:9.5px}

/* Saved-lists dock mock (states 12-13). Board rows are a simplified static
   stand-in — see caption. */
.dock-scene{display:flex;width:1440px;height:900px;background:var(--color-bg-canvas);position:relative;overflow:hidden}
.mock-board{flex:1 1 auto;background:var(--color-bg-panel);position:relative;padding:16px}
.mock-row{display:flex;align-items:center;gap:10px;height:26px;padding:0 8px;border-bottom:1px solid var(--color-line-hairline);
  background:var(--color-row-default-bg);font:500 10.5px var(--font-sans);color:var(--color-text-ink)}
.mock-row:nth-child(odd){background:var(--color-row-alt-bg)}
.mock-row .band{width:6px;align-self:stretch;border-radius:2px}
.mock-row .mid{font:700 10px var(--font-mono);color:var(--color-text-mono);width:70px}
.mock-row .mname{flex:1 1 auto}
.mock-marker{width:11px;height:11px;border-radius:2px;display:inline-block;transform:rotate(45deg)}
.mock-marker.selected{outline:2px solid var(--color-accent-purple);outline-offset:2px}
.sel-chip{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:10px;
  padding:8px 14px;border-radius:var(--radius-pill);background:var(--color-dialog-elev);
  box-shadow:0 6px 20px var(--color-shadow-soft);font:500 10.5px var(--font-sans);color:var(--color-text-ink);
  border:1px solid var(--color-line-default);z-index:4}
.sel-chip b{font-weight:700}
.sel-chip button{font:600 10px var(--font-sans);padding:3px 9px;border-radius:5px;border:1px solid var(--color-btn-secondary-outline);
  background:var(--color-btn-secondary-bg);color:var(--color-btn-secondary-text);cursor:pointer}
.lists-panel{width:320px;flex:0 0 auto;background:var(--color-bg-elevated);border-left:1px solid var(--color-line-default);
  display:flex;flex-direction:column;box-shadow:-4px 0 14px var(--color-shadow-soft)}
.lists-panel.dock-left{border-left:none;border-right:1px solid var(--color-line-default);
  box-shadow:4px 0 14px var(--color-shadow-soft);order:-1}
.lp-head{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--color-line-default)}
.lp-title{font:600 12px var(--font-sans);flex:1 1 auto}
.lp-icon{width:20px;height:20px;border-radius:5px;border:1px solid var(--color-border-panel);
  background:var(--color-bg-panel);color:var(--color-text-on-panel);display:inline-flex;align-items:center;
  justify-content:center;font-size:11px;cursor:pointer}
.lp-select-row{display:flex;align-items:center;gap:6px;padding:10px 14px;border-bottom:1px solid var(--color-line-hairline)}
.lp-select{flex:1 1 auto;font:600 11px var(--font-sans);padding:4px 8px;border-radius:6px;
  border:1px solid var(--color-input-border);background:var(--color-bg-elevated);color:var(--color-text-ink)}
.lp-items{flex:1 1 auto;overflow:auto;padding:4px 0}
.lp-item{display:flex;align-items:center;gap:8px;padding:7px 14px;border-bottom:1px solid var(--color-line-hairline);font:500 10.5px var(--font-sans)}
.lp-item .lid{font:700 10px var(--font-mono);color:var(--color-text-mono);width:66px}
.lp-item .ltitle{flex:1 1 auto;color:var(--color-text-ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lp-item .lfin{color:var(--color-text-muted);font-size:9.5px;width:54px}
.lp-item .lremove{background:none;border:none;color:var(--color-text-muted);cursor:pointer;font-size:11px;padding:0 2px}
.lp-foot{padding:12px 14px;border-top:1px solid var(--color-line-default);display:flex;flex-direction:column;gap:6px}
.lp-foot .imp-primary,.lp-foot .imp-secondary{width:100%;text-align:center}
"""


def doc(theme, width, css_extra, body, height=None):
    h = f"height:{height}px;" if height else ""
    return f"""<!DOCTYPE html><html lang="en" data-theme="{theme}"><head><meta charset="UTF-8">
<style>{TOKENS_LIGHT}{TOKENS_DARK}{TOKENS_ROOT}{CARD_CSS}{NEW_CSS}{css_extra}
html,body{{width:{width}px;{h}margin:0}}</style></head><body>{body}</body></html>"""


def health_dots(active):
    vals = [0, 1, 2, 3, 4]
    titles = {0: "N/A", 1: "On track", 2: "Done", 3: "At risk", 4: "Critical"}
    out = []
    for v in vals:
        sel = " selected" if v == active else ""
        out.append(f'<span class="health-dot mh-{v}{sel}" title="{titles[v]}"></span>')
    return "".join(out)


def card_shell(status_cls, code, status_text, title, subtitle, start, finish, finish_extra,
               progress, progress_dirty, saveactions_visible, comment_html, marker_extra="",
               title_extra="", float_val="6"):
    save_html = "" if not saveactions_visible else (
        '<span class="ms-save-actions"><button class="ms-act">&#128190;</button>'
        '<button class="ms-act">&#128190; &amp; Close</button></span>'
    )
    close_html = '<button class="ms-close">&#10005;</button><span class="ms-head-spacer"></span>' + save_html
    return f"""<div class="ms-dialog {status_cls}">
  <div class="ms-dialog-head">{close_html}</div>
  <div class="ms-title-row">
    <div class="ms-title-col">
      <div class="ms-heading">
        <span class="ms-icon-btn"><svg width="13" height="13"><polygon points="6.5,1 12,6.5 6.5,12 1,6.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg></span>
        <span class="ms-code">{code}</span>{marker_extra}
        <span class="ms-status">{status_text}</span>
      </div>
      <p class="ms-sub">Site Infrastructure &middot; Deliverables</p>
      <div class="ms-title">{title}</div>{title_extra}
    </div>
    <div class="ms-float-col"><div class="ms-float-val">{float_val}</div><span class="ms-float-lbl">float</span></div>
  </div>
  <div class="ms-schedule">
    <div class="ms-field"><span class="ms-lbl">Start</span><div class="ms-date">{start}</div></div>
    <div class="ms-field"><span class="ms-lbl">Finish</span>{finish}</div>
    <div class="ms-field ms-prog-field"><span class="ms-lbl">Progress</span>{progress}</div>
  </div>
  <div class="ms-progress-track"><div class="ms-progress-fill" style="width:{progress_dirty}%"></div></div>
  {comment_html}
</div>"""


def field_dirty(label_html, value, extra_after=""):
    return f'<div class="field-row"><div class="ms-date ms-dirty-field">{value}</div>{extra_after}</div>'


def old_comment_block():
    return """<div class="ms-comment-block">
    <div class="ms-comment-head"><span class="ms-lbl" style="margin-bottom:0"><span class="ms-comment-dot" style="width:6px;height:6px;border-radius:50%;background:var(--color-comment-indicator);display:inline-block;margin-right:5px"></span>Comment</span>
    <span class="ms-head-divider"></span><span class="ms-lbl" style="margin-bottom:0">Health</span>
    <div class="ms-health-dots">""" + health_dots(1) + """</div></div>
    <textarea style="width:100%;min-height:40px;font-family:var(--font-sans);font-size:10.5px;padding:6px 7px;border-radius:6px;border:1px solid var(--color-line-default);background:var(--color-bg-elevated);color:var(--color-text-ink)" placeholder="Notes on this milestone&#8230;">Waiting on structural sign-off before this can move.</textarea>
  </div>"""


def thread_block(clear_confirm=False, health=2):
    entries_recent = [
        ("Reissued to survey with the revised bench elevations.", "23-Sep 14:05", "DD 29-Aug", False),
        ("Confirmed scope with site team, no change to footprint.", "22-Sep 09:40", "DD 29-Aug", False),
        ("Waiting on structural sign-off before this can move.", "20-Sep 16:12", "DD 29-Aug", False),
    ]
    entries_older = [
        ("Draft layout circulated for comment.", "12-Aug 11:02", "DD 15-Aug", True),
        ("Kickoff note: aligns with TSF footprint v2.", "07-Aug 08:55", "DD 15-Aug", True),
    ]
    def render(entries):
        rows = []
        for body, meta, pill, prior in entries:
            cls = " prior" if prior else ""
            rows.append(f"""<div class="thread-entry{cls}"><p class="thread-body">{body}</p>
        <div class="thread-meta"><span class="thread-time">{meta}</span><span class="thread-pill">{pill}</span></div></div>""")
        return "".join(rows)

    head_right = ('<div class="clear-confirm"><span>Clear 4 comments?</span>'
                  '<button class="btn-danger">Clear</button><button class="btn-cancel">Cancel</button></div>'
                  if clear_confirm else
                  '<button class="thread-clear">Clear comments</button>')

    body = f"""<div class="ms-comment-block">
    <div class="thread-head"><span class="thread-title">Comments (4)</span>
      <span class="ms-head-divider" style="height:14px"></span>
      <div class="ms-health-dots">{health_dots(health)}</div>
    </div>
    {'<input class="thread-add" placeholder="Add a comment&#8230;">' if not clear_confirm else ''}
    {render(entries_recent)}
    <button class="thread-more">Show 2 earlier</button>
    """
    if clear_confirm:
        body = f"""<div class="ms-comment-block">
    <div class="thread-head"><span class="thread-title">Comments (4)</span>
      <span class="ms-head-divider" style="height:14px"></span>
      <div class="ms-health-dots">{health_dots(health)}</div>
    </div>
    {head_right}
    {render(entries_recent)}
    <button class="thread-more">Show 2 earlier</button>
  </div>"""
        return body
    return body + "</div>"


STATES = {}


def add(id_, slug, title, caption, theme, width, html_body, height=None, css_extra=""):
    STATES[id_] = dict(slug=slug, title=title, caption=caption, theme=theme,
                        width=width, height=height, html=doc(theme, width, css_extra, html_body, height))


# 01 — pristine (P45 baseline, unchanged)
body01 = card_shell("status-track", "SNIP-207", "On track",
                     "Site Infrastructure Design Complete",
                     None, "12-Aug-26", '<div class="ms-date">29-Oct-26</div>',
                     None, '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">40</span><span class="ms-prog-pct">%</span></span>',
                     40, False, old_comment_block())
add("01", "01-card-pristine", "01 &middot; Card pristine (light)",
    "P45 baseline, unchanged. Reference point for every diff below.",
    "light", 306, f'<div class="frame-pad">{body01}</div>')

# 02 — editing: Finish + Progress dirty, each with a discard x, focus ring on Finish
finish_02 = ('<div class="field-row"><div class="ms-date ms-dirty-field" tabindex="0" '
             'style="outline:2px solid var(--color-accent-purple);outline-offset:1px">05-Nov-26</div>'
             '<button class="field-x" title="Discard this change">&#10005;</button></div>')
prog_02 = ('<span class="ms-prog-edit changed" style="display:inline-flex"><span class="ms-prog-input" '
           'style="color:var(--color-accent-ink)">55</span><span class="ms-prog-pct" style="color:var(--color-accent-ink)">%</span></span>'
           '<button class="field-x" title="Discard this change">&#10005;</button>')
body02 = card_shell("status-track", "SNIP-207", "On track",
                     "Site Infrastructure Design Complete", None,
                     "12-Aug-26", finish_02, None, prog_02, 55, True, old_comment_block())
add("02", "02-card-editing", "02 &middot; Editing (Finish + Progress dirty)",
    "NEW: per-field &times; beside each edited-unsaved value, 12x16px icon-button hit area "
    "using --color-btn-icon-hover-bg/--color-btn-icon-pressed-bg. Tooltip “Discard this change”. "
    "Save / Save &amp; Close pair shown per P43. Focus ring visible on Finish (the one focused control).",
    "light", 306, f'<div class="frame-pad">{body02}</div>')

# 03 — saved marks (asterisk), one tooltip open
title_extra_03 = ''
finish_03 = '<div class="ms-date">05-Nov-26<sup class="saved-mark" id="fmark">*</sup></div>'
prog_03 = ('<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" '
           'style="text-align:right">55</span><span class="ms-prog-pct">%</span></span>'
           '<sup class="saved-mark">*</sup>')
title_html_03 = 'Site Infrastructure Design Complete<sup class="saved-mark">*</sup>'
body03 = card_shell("status-track", "SNIP-207", "On track", title_html_03, None,
                     "12-Aug-26", finish_03, None, prog_03, 55, False, old_comment_block())
tip03 = ('<div class="demo-tip" style="top:168px;left:34px">Source: 29-Oct-26'
         '<div class="tip-line2">Saved 23-Sep 14:05 (DD 29-Aug)</div></div>')
add("03", "03-card-saved", "03 &middot; Saved (asterisk marks)",
    "NEW: replaces the P44 purple dot with a superscript * in --color-accent-ink on Finish, "
    "Progress and Name. One tooltip shown open on Finish: two lines, source value then save time "
    "and the deliverables-date period it was saved against.",
    "light", 306, f'<div class="frame-pad" style="position:relative">{body03}{tip03}</div>')

# 04 — comment thread, two periods, collapsed to 3
body04 = card_shell("status-risk", "SNIP-215", "At risk",
                     "Structural &amp; Concrete Design", None,
                     "01-Sep-26", '<div class="ms-date">30-Nov-26</div>', None,
                     '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">22</span><span class="ms-prog-pct">%</span></span>',
                     22, False, thread_block(health=3))
add("04", "04-card-comment-thread", "04 &middot; Comment thread (collapsed)",
    "NEW: replaces the single textarea. Header “Comments (4)” + health dots + right-aligned "
    "“Clear comments” text button. Add-comment input, then newest-first entries. Collapsed to "
    "latest 3 with “Show 2 earlier”. Two prior-period entries (dimmed, pill “DD 15-Aug”) "
    "are hidden behind that link; visible entries carry “DD 29-Aug”.",
    "light", 306, f'<div class="frame-pad">{body04}</div>')

# 05 — clear confirmation inline
body05 = card_shell("status-risk", "SNIP-215", "At risk",
                     "Structural &amp; Concrete Design", None,
                     "01-Sep-26", '<div class="ms-date">30-Nov-26</div>', None,
                     '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">22</span><span class="ms-prog-pct">%</span></span>',
                     22, False, thread_block(clear_confirm=True, health=3))
add("05", "05-card-clear-confirm", "05 &middot; Clear comments confirmation",
    "NEW: “Clear comments” replaced inline by “Clear 4 comments? [Clear] [Cancel]”. "
    "Clear uses --color-status-crit / --color-crit-tint-bg (the app's existing danger/critical "
    "role — no separate danger-button token exists, so this is the closest real role).",
    "light", 306, f'<div class="frame-pad">{body05}</div>')

# 06 — USR-007 NEW badge + remap variant
body06a = card_shell("status-track", "USR-007", "On track",
                      'New site access gate", "', None,
                      "&mdash;", '<div class="ms-date">15-Dec-26</div>', None,
                      '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">0</span><span class="ms-prog-pct">%</span></span>',
                      0, False, old_comment_block(),
                      marker_extra='<span class="new-badge">New</span>')
body06a = body06a.replace('New site access gate", "', 'New site access gate')
body06b = card_shell("status-track", "USR-007", "On track",
                      "New site access gate", None,
                      "&mdash;", '<div class="ms-date">15-Dec-26</div>', None,
                      '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">0</span><span class="ms-prog-pct">%</span></span>',
                      0, False, old_comment_block(),
                      marker_extra='<span class="remap">&rarr; ENG-4410</span>')
add("06", "06-card-user-added-new", "06 &middot; User-added milestone (NEW / remapped)",
    "NEW: a user-added milestone not yet in the schedule shows a NEW pill beside #ms-code "
    "(accent-wash / accent-ink, the same pairing .ms-type-opt.active already uses for "
    "“this is the called-out one”). Second card: once the import maps it to a real "
    "activity, the pill is replaced by “USR-007 &rarr; ENG-4410” in mono, muted text.",
    "light", 306, f'<div class="frame-pad">{body06a}</div><div class="frame-pad">{body06b}</div>')

# 07 — schedule changed glyph
finish_07 = ('<div class="field-row"><div class="ms-date">29-Oct-26</div>'
             '<button class="sched-changed" title="Schedule changed: was 15-Oct-26. Review in Import changes.">&#8635;</button></div>')
body07 = card_shell("status-track", "SNIP-207", "On track",
                     "Site Infrastructure Design Complete", None,
                     "12-Aug-26", finish_07, None,
                     '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">40</span><span class="ms-prog-pct">%</span></span>',
                     40, False, old_comment_block())
tip07 = ('<div class="demo-tip" style="top:168px;left:34px">Schedule changed: was 15-Oct-26.'
         '<div class="tip-line2">Review in Import changes.</div></div>')
add("07", "07-card-schedule-changed", "07 &middot; Schedule-changed, pending review",
    "NEW: a distinct &#8635; glyph on Finish (--color-status-risk ink, the app's existing "
    "“needs attention” role) marks a field whose incoming schedule value differs from what "
    "is shown, pending an import decision — separate from both &times; (discard an edit) and "
    "the * (already-saved edit).",
    "light", 306, f'<div class="frame-pad" style="position:relative">{body07}{tip07}</div>')

# 08 — 03 + 04 combined, dark theme
body08 = card_shell("status-track", "SNIP-207", "On track",
                     'Site Infrastructure Design Complete<sup class="saved-mark">*</sup>', None,
                     "12-Aug-26", finish_03, None, prog_03, 55, False, thread_block(health=2))
add("08", "08-card-dark", "08 &middot; Saved marks + comment thread, dark theme",
    "States 03 and 04 combined, rendered under html[data-theme=\"dark\"] using the app's own "
    "dark-theme token block unmodified.",
    "dark", 306, f'<div class="frame-pad">{body08}</div>')

# 09 — phone bottom sheet
sheet_card = card_shell("status-track", "SNIP-207", "On track",
                         "Site Infrastructure Design Complete", None,
                         "12-Aug-26", '<div class="ms-date">29-Oct-26</div>', None,
                         '<span class="ms-prog-edit" style="display:inline-flex"><span class="ms-prog-input" style="text-align:right">40</span><span class="ms-prog-pct">%</span></span>',
                         40, False, thread_block(health=2))
body09 = f"""<div class="sheet-wrap"><div class="sheet"><div class="drag-handle"></div>{sheet_card}
  <div class="sheet-savebar"><button class="toggle-btn">Cancel</button><button class="ms-act">&#128190; &amp; Close</button></div>
</div></div>"""
add("09", "09-card-phone-sheet", "09 &middot; Phone width (390px), bottom sheet",
    "Card becomes a full-width bottom sheet with rounded top corners and a drag handle. Save "
    "controls move to a sticky bar pinned to the bottom of the sheet so they stay reachable "
    "under the keyboard.",
    "light", 390, body09, height=640)

# 10 — import review summary
def imp_row(cat, count, action, conflict=False):
    cls = " conflict" if conflict else ""
    return f'<div class="imp-row{cls}"><span class="imp-cat">{cat}</span><span class="imp-count">{count}</span><span class="imp-action">{action}</span><span class="imp-chev">&#8250;</span></div>'

imp10 = f"""<div class="imp-dialog">
  <div class="imp-head"><h3 class="imp-title">Review schedule changes &middot; DD 12-Sep vs DD 29-Aug</h3></div>
  <div class="imp-rows">
    {imp_row("Edits taken up", 12, "Confirm")}
    {imp_row("Edits not taken up", 3, "Retain")}
    {imp_row("Conflicts", 2, "Review, required", conflict=True)}
    {imp_row("Schedule changes, no edit", 27, "Acknowledge")}
    {imp_row("New in schedule", 5, "Confirm match")}
    {imp_row("Removed from schedule", 1, "Acknowledge")}
    {imp_row("Prior-period comments", 9, "Retain")}
  </div>
  <div class="imp-foot"><span class="imp-note">2 conflicts need a decision</span>
    <button class="imp-secondary">Close</button><button class="imp-primary">Apply defaults</button>
  </div>
</div>"""
add("10", "10-import-review-summary", "10 &middot; Import review — summary",
    "NEW surface. One row per change category with its count, default action and a chevron to "
    "expand. Conflicts is highlighted with --color-crit-tint-bg / --color-crit-text since it is "
    "the only category requiring a decision before Apply defaults can be trusted.",
    "light", 560, f'<div class="frame-pad">{imp10}</div>')

# 11 — import review expanded category
def tbl_row(id_, name, field, was, now, period, ticked):
    cls = ' class="ticked"' if ticked else ''
    chk = 'checked' if ticked else ''
    action = '' if ticked else '<span class="imp-default">Acknowledge (default)</span>'
    return f"""<tr{cls}><td><input type="checkbox" {chk}></td><td class="imp-cat" style="font:700 10px var(--font-mono);color:var(--color-text-mono)">{id_}</td>
    <td>{name}</td><td>{field}</td><td class="imp-was-now">{was} &rarr; {now}</td><td>{period}</td><td>{action}</td></tr>"""

rows = [
    ("SNIP-207", "Site Infrastructure Design Complete", "Finish", "15-Oct-26", "29-Oct-26", "DD 12-Sep", True),
    ("SNIP-224", "CAPEX and OPEX Project Review", "Finish", "02-Nov-26", "09-Nov-26", "DD 12-Sep", True),
    ("SNIP-218", "Project Execution Plan (PEP)", "Finish", "20-Sep-26", "27-Sep-26", "DD 12-Sep", False),
    ("SNIP-221", "Final Site Layout – Issued for Use", "Start", "01-Oct-26", "08-Oct-26", "DD 12-Sep", False),
    ("SNIP-211", "Owners Cost Data Entry", "Finish", "14-Nov-26", "21-Nov-26", "DD 12-Sep", False),
]
imp11 = f"""<div class="imp-dialog" style="width:640px">
  <div class="imp-head"><h3 class="imp-title">Schedule changes, no edit &middot; 27 rows</h3></div>
  <div class="imp-selbar">2 selected as exceptions &middot; Action
    <select><option>Retain as note</option></select>
    <button class="imp-primary">Update selected</button>
  </div>
  <table class="imp-table"><thead><tr><th></th><th>ID</th><th>Name</th><th>Field</th><th>Was &rarr; Now</th><th>Period</th><th></th></tr></thead>
  <tbody>{"".join(tbl_row(*r) for r in rows)}</tbody></table>
  <div class="imp-foot"><button class="imp-secondary">Back</button><button class="imp-primary">Apply defaults</button></div>
</div>"""
add("11", "11-import-review-expanded", "11 &middot; Import review — category expanded",
    "“Schedule changes, no edit” expanded into a row table: checkbox, ID, name, field, "
    "was &rarr; now, period. Two rows ticked as exceptions surface a selection bar above the "
    "table (“2 selected as exceptions · Action · Update selected”); untouched rows show "
    "their default action inline instead of a control.",
    "light", 680, f'<div class="frame-pad">{imp11}</div>')


def mock_board_rows(n=22):
    bands = ["--color-band-1", "--color-band-2", "--color-band-3", "--color-band-4", "--color-band-5"]
    names = ["Snip Electrical Load List", "Electrical Equipment List", "NPI Major Infrastructure Building List",
             "Eskay EEL Inputs", "Snip MEL Inputs", "Fire Detection and Protection Design",
             "TSF Model & Cost Estimate", "Site Infrastructure Design Complete", "Owners Cost Data Entry",
             "Construction Execution Plan", "Structural & concrete Design", "Earthworks 3D Model",
             "Project Execution Plan (PEP)", "Final Site Layout - Issued for Use",
             "Preliminary Earthworks MTO", "Final Design Review", "CAPEX and OPEX Project Review"]
    rows = []
    for i in range(n):
        band = bands[i % len(bands)]
        name = names[i % len(names)]
        mid = f"SNIP-{160 + i*7}"
        selected = i in (3, 9, 14)
        mk = f'<span class="mock-marker{" selected" if selected else ""}" style="background:var({band})"></span>'
        rows.append(f'<div class="mock-row"><span class="band" style="background:var({band})"></span>'
                    f'<span class="mid">{mid}</span><span class="mname">{name}</span>{mk}</div>')
    return "".join(rows)

CHIP = ('<div class="sel-chip"><b>3 selected</b> &middot; Add to “Critical path review” &middot; '
        '<button>Add to &#9662;</button><button>Filter</button><button>Clear</button></div>')

LP_ITEMS = [
    ("SNIP-207", "Site Infrastructure Design Complete", "29-Oct-26", "mh-1"),
    ("SNIP-224", "CAPEX and OPEX Project Review", "09-Nov-26", "mh-3"),
    ("SNIP-218", "Project Execution Plan (PEP)", "27-Sep-26", "mh-2"),
    ("SNIP-215", "Structural & concrete Design", "30-Nov-26", "mh-3"),
    ("SNIP-221", "Final Site Layout - Issued for Use", "08-Oct-26", "mh-1"),
    ("SNIP-211", "Owners Cost Data Entry", "21-Nov-26", "mh-0"),
    ("SNIP-188", "NPI Major Infrastructure Building List", "12-Oct-26", "mh-2"),
    ("SNIP-202", "Fire Detection and Protection Design", "18-Oct-26", "mh-1"),
]

def lists_panel(dock_left=False):
    items = "".join(
        f'<div class="lp-item"><span class="lid">{i}</span><span class="ltitle">{t}</span>'
        f'<span class="lfin">{f}</span><span class="health-dot {h}" style="border:1.2px solid var(--color-health-rim);width:9px;height:9px;display:inline-block;border-radius:50%"></span>'
        f'<button class="lremove" title="Remove">&#10005;</button></div>'
        for i, t, f, h in LP_ITEMS)
    dock_cls = " dock-left" if dock_left else ""
    toggle_icon = "&#9703;" if not dock_left else "&#9703;"
    return f"""<div class="lists-panel{dock_cls}">
  <div class="lp-head"><span class="lp-title">Saved lists</span>
    <button class="lp-icon" title="Dock left">&#9707;</button>
    <button class="lp-icon" title="Dock right">&#9706;</button>
    <button class="lp-icon" title="Close">&#10005;</button></div>
  <div class="lp-select-row"><select class="lp-select"><option>Critical path review (8)</option></select>
    <button class="lp-icon" title="New">+</button><button class="lp-icon" title="Rename">&#9998;</button>
    <button class="lp-icon" title="Delete">&#128465;</button></div>
  <div class="lp-items">{items}</div>
  <div class="lp-foot"><button class="imp-primary">Filter board to list</button>
    <button class="imp-secondary">Add selection (3)</button></div>
</div>"""

body12 = f'<div class="dock-scene"><div class="mock-board">{mock_board_rows()}{CHIP}</div>{lists_panel(False)}</div>'
add("12", "12-lists-panel-docked-right", "12 &middot; Saved lists panel, docked right (1440x900)",
    "NEW surface. STATIC MOCK, not the real app loaded in Chromium — the real board is an "
    "11k-line generated table with its own dependency-line SVG overlay, so reproducing it here "
    "faithfully was judged riskier than a clearly-labelled simplified stand-in. Real elements "
    "shown to real scale/tokens: 3 markers get a 2px accent outline + offset (.ms-selected), a "
    "floating selection chip bottom-centre, and #lists-panel docked full-height at 320px with "
    "header, dock-side toggle, list selector, item rows and footer actions. Board is shifted "
    "left by the panel, as it would be when docked.",
    "light", 1440, body12, height=900)

body13 = f'<div class="dock-scene">{lists_panel(True)}<div class="mock-board">{mock_board_rows()}{CHIP}</div></div>'
add("13", "13-lists-panel-docked-left-dark", "13 &middot; Saved lists panel, docked left, dark",
    "Same panel docked left instead of right, dark theme. Same static-mock caveat as state 12.",
    "dark", 1440, body13, height=900)


def render_all(chrome):
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for id_, s in sorted(STATES.items()):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(s["html"])
            html_path = f.name
        w = s["width"] + 56
        h = (s["height"] or 900) + (0 if s["height"] else 0)
        png_path = PNG_DIR / f"{s['slug']}.png"
        cmd = [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
               f"--window-size={w},{h}", f"--screenshot={png_path}", f"file://{html_path}"]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        results.append((id_, s["slug"], png_path))
        pathlib.Path(html_path).unlink(missing_ok=True)
    return results


def build_review_page(results):
    frames = []
    for id_ in sorted(STATES.keys()):
        s = STATES[id_]
        iframe_h = (s["height"] or 900) + 40
        frames.append(f"""<section class="frame">
  <h2>{s['title']}</h2>
  <p class="caption">{s['caption']}</p>
  <div class="frame-box"><iframe srcdoc="{escape_srcdoc(s['html'])}" style="width:{s['width']+40}px;height:{iframe_h}px;border:0" loading="lazy"></iframe></div>
</section>""")
    page = f"""<title>Milestone Card Renders</title>
<style>
:root{{--bg:#f3f4f7;--surface:#ffffff;--ink:#17191c;--muted:#575c67;--faint:#6f7480;--line:#e1e3e8;--head:#2e4f82;--head-ink:#f4f5f8;--head-muted:#c4d2e8;--stage:#fbfbfc}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#14171c;--surface:#1c2027;--ink:#e6e8ec;--muted:#a6adba;--faint:#8b93a1;--line:#2c323c;--head:#1f3558;--head-ink:#e9eef6;--head-muted:#a9bad4;--stage:#171a20}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#14171c;--surface:#1c2027;--ink:#e6e8ec;--muted:#a6adba;--faint:#8b93a1;--line:#2c323c;--head:#1f3558;--head-ink:#e9eef6;--head-muted:#a9bad4;--stage:#171a20}}
body{{font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink);padding-inline:16px}}
.wrap{{max-width:1560px;margin:0 auto;padding-block:20px 32px;display:flex;flex-direction:column;gap:20px}}
header{{background:var(--head);color:var(--head-ink);border-radius:10px;padding:20px 22px}}
header h1{{margin:0 0 6px;font-size:18px;text-wrap:balance}}
header p{{margin:0;font-size:13px;line-height:1.5;color:var(--head-muted);max-width:75ch}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(360px,100%),1fr));gap:20px}}
.frame{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px;min-width:0}}
.frame h2{{margin:0 0 4px;font-size:13px}}
.frame .caption{{margin:0 0 10px;font-size:12px;line-height:1.5;color:var(--muted)}}
.frame-box{{overflow-x:auto;border:1px dashed var(--line);border-radius:6px;background:var(--stage)}}
footer{{font-size:12px;color:var(--faint)}}
</style>
<div class="wrap">
<header><h1>D-01 renders for review</h1>
<p>Milestone card, import review dialog and saved lists panel, drawn from the P45 card's own CSS and tokens. Each caption says what is new against P45. Wide frames scroll sideways inside their own box. The board behind the lists panel is a static stand-in; the panel itself is to scale.</p></header>
<main>{''.join(frames)}</main>
<footer>Built by tools/d01_render.py. PNG copies are in docs/mockups/D-01/png/.</footer>
</div>"""
    (OUT_DIR / "render_review.html").write_text(page, encoding="utf-8")


def escape_srcdoc(html):
    return html.replace("&", "&amp;").replace('"', "&quot;")


def main():
    chrome = find_chrome()
    results = render_all(chrome)
    build_review_page(results)
    print(f"Wrote {len(results)} PNGs to {PNG_DIR}")
    print(f"Wrote {OUT_DIR/'render_review.html'}")


if __name__ == "__main__":
    main()
