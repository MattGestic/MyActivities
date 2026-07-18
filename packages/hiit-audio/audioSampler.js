import {
  bootAudioContext,
  getCueDuration,
  getVolume,
  playTimerEvent,
  resumeAudioContext,
  setVolume,
  stopAllCues,
} from "./audioEngine.js";

const CUES = Object.freeze([
  { event: "programmeStart", label: "Programme start", detail: "Opening bell" },
  { event: "blockStart", label: "Block start", detail: "Let’s go!" },
  { event: "activityStart", label: "Activity start", detail: "Gooo" },
  { event: "activityEnd", label: "Activity end", detail: "Female 3, 2, 1" },
  { event: "restStart", label: "Rest start", detail: "Woohoo" },
  { event: "restEnd", label: "Rest end", detail: "Three short beeps" },
  { event: "blockEnd", label: "Block end", detail: "Yay" },
  {
    event: "programmeEnd",
    label: "Programme end",
    detail: "Well done + You go girl",
    badge: "2-file queue",
  },
  { event: "postProgramme", label: "Queue item 2", detail: "You go girl" },
]);

export class HiitAudioSampler extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._ready = false;
    this._loading = false;
    this._error = "";
    this._preparePromise = null;
    this._previewTimer = 0;
  }

  connectedCallback() {
    this.render();
    this.bindEvents();
    if (this.mode === "dialog") {
      this.shadowRoot.querySelector("dialog").showModal();
    } else {
      this.shadowRoot.querySelector(".close").focus();
    }
  }

  disconnectedCallback() {
    window.clearTimeout(this._previewTimer);
  }

  get mode() {
    return this.getAttribute("mode") === "fullscreen" ? "fullscreen" : "dialog";
  }

  async prepareAudio() {
    if (this._ready) return this;
    if (this._preparePromise) return this._preparePromise;

    this._loading = true;
    this.updateState();
    this._preparePromise = (async () => {
      try {
        await bootAudioContext();
        await resumeAudioContext();
        this._ready = true;
        this._error = "";
        this.updateDurations();
        this.dispatchEvent(new CustomEvent("audio-sampler-ready", { bubbles: true }));
      } catch (error) {
        this._error = error.message;
        this._preparePromise = null;
      } finally {
        this._loading = false;
        this.updateState();
      }
      return this;
    })();

    return this._preparePromise;
  }

  close() {
    if (this._ready) stopAllCues();
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog?.open) dialog.close();
    this.dispatchEvent(new CustomEvent("audio-sampler-close", { bubbles: true }));
    this.remove();
  }

  render() {
    const frameTag = this.mode === "dialog" ? "dialog" : "section";
    const frameClass = this.mode === "dialog" ? "frame frame--dialog" : "frame frame--fullscreen";
    const cueMarkup = CUES.map((cue) => `
      <button class="cue" type="button" data-event="${cue.event}" disabled aria-pressed="false">
        <span class="cue__copy">
          <span class="cue__label">${cue.label}</span>
          <span class="cue__detail">${cue.detail}</span>
          ${cue.badge ? `<span class="badge">${cue.badge}</span>` : ""}
        </span>
        <span class="cue__meta">
          <span class="cue__duration" data-duration="${cue.event}">—</span>
          <span class="cue__play" aria-hidden="true">▶</span>
        </span>
      </button>
    `).join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          font-family: var(--font-body);
          color: var(--color-text-primary);
          --audio-action-foreground: var(--color-bg-app);
        }
        :host-context([data-theme="light"]) { --audio-action-foreground: var(--color-text-primary); }
        *, *::before, *::after { box-sizing: border-box; }
        button, input { font: inherit; }
        button { -webkit-tap-highlight-color: transparent; }
        [hidden] { display: none !important; }
        .frame {
          padding: 0;
          color: var(--color-text-primary);
          background: var(--color-bg-app);
          border: 1px solid var(--color-border-subtle);
          overflow: hidden;
        }
        .frame--dialog {
          width: min(calc(100vw - 24px), 540px);
          height: min(calc(100dvh - 24px), 780px);
          max-width: none;
          max-height: none;
          border-radius: 16px;
          box-shadow: 0 24px 64px color-mix(in srgb, var(--color-bg-app) 74%, transparent);
        }
        .frame--dialog::backdrop {
          background: color-mix(in srgb, var(--color-bg-app) 78%, transparent);
          backdrop-filter: blur(6px);
        }
        .frame--fullscreen {
          position: fixed;
          inset: 0;
          z-index: 1000;
          width: 100%;
          height: 100dvh;
          border: 0;
          border-radius: 0;
        }
        .screen { display: flex; flex-direction: column; height: 100%; }
        .topbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          min-height: 68px;
          padding: 12px 20px;
          background: var(--color-bg-surface);
          border-bottom: 1px solid var(--color-border-subtle);
        }
        .eyebrow, .section-label, .cue__label, .badge, .status {
          font-family: var(--font-display);
          text-transform: uppercase;
        }
        .eyebrow {
          margin: 0 0 4px;
          color: var(--color-action-primary);
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.2em;
        }
        h1 {
          margin: 0;
          font-family: var(--font-display);
          font-size: 24px;
          line-height: 1.1;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }
        .close {
          flex: 0 0 44px;
          width: 44px;
          height: 44px;
          border: 1px solid var(--color-border-subtle);
          border-radius: 12px;
          color: var(--color-text-secondary);
          background: var(--color-bg-card);
          font-size: 26px;
          line-height: 1;
          cursor: pointer;
        }
        .close:hover { color: var(--color-text-primary); background: var(--color-bg-card-elevated); }
        .close:active { transform: scale(0.96); }
        .main {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          scrollbar-gutter: stable;
        }
        .intro {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 20px;
        }
        .intro p {
          flex: 1 1 auto;
          min-width: 0;
          max-width: 36rem;
          margin: 0;
          color: var(--color-text-secondary);
          font-size: 14px;
          line-height: 1.5;
        }
        .status {
          flex: 0 0 148px;
          width: 148px;
          min-width: 148px;
          max-width: 148px;
          height: 26px;
          padding: 4px 8px;
          overflow: hidden;
          border-radius: 6px;
          color: var(--color-text-secondary);
          background: var(--color-bg-card);
          border: 1px solid var(--color-border-subtle);
          font-size: 10px;
          font-weight: 700;
          line-height: 16px;
          letter-spacing: 0.12em;
          text-align: center;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .status[data-state="ready"], .status[data-state="playing"] {
          color: var(--color-action-primary);
          border-color: color-mix(in srgb, var(--color-action-primary) 36%, transparent);
          background: color-mix(in srgb, var(--color-action-primary) 10%, var(--color-bg-card));
        }
        .status[data-state="error"] { color: var(--color-danger); }
        .volume-card {
          margin-bottom: 24px;
          padding: 16px;
          border: 1px solid var(--color-border-subtle);
          border-radius: 16px;
          background: var(--color-bg-surface);
        }
        .volume-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .section-label {
          color: var(--color-text-muted);
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.18em;
        }
        .volume-value {
          color: var(--color-text-primary);
          font-family: var(--font-mono);
          font-size: 20px;
          font-weight: 700;
          font-variant-numeric: tabular-nums;
        }
        input[type="range"] {
          width: 100%;
          height: 44px;
          margin: 8px 0 0;
          accent-color: var(--color-action-primary);
          cursor: pointer;
        }
        .enable {
          width: 100%;
          min-height: 48px;
          margin-top: 12px;
          padding: 12px 20px;
          border: 0;
          border-radius: 12px;
          color: var(--audio-action-foreground);
          background: var(--color-action-primary);
          font-family: var(--font-display);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          cursor: pointer;
        }
        .enable:hover { background: var(--color-action-primary-hover); }
        .enable:active { background: var(--color-action-primary-pressed); }
        .enable:disabled { color: var(--color-text-muted); background: var(--color-action-disabled); cursor: wait; }
        .error { margin: 12px 0 0; color: var(--color-danger); font-size: 13px; }
        .sounds-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--color-border-subtle);
        }
        .sounds-hint { color: var(--color-text-muted); font-size: 12px; }
        .cue-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
        .cue {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          width: 100%;
          min-height: 76px;
          padding: 12px;
          text-align: left;
          color: var(--color-text-primary);
          background: var(--color-bg-surface);
          border: 1px solid var(--color-border-subtle);
          border-radius: 16px;
          cursor: pointer;
          transition: background 0.15s, border-color 0.15s, transform 0.15s;
        }
        .cue:hover { background: var(--color-bg-card); border-color: color-mix(in srgb, var(--color-action-primary) 32%, var(--color-border-subtle)); }
        .cue:active { transform: scale(0.985); }
        .cue[aria-pressed="true"] {
          border-color: var(--color-action-primary);
          background: color-mix(in srgb, var(--color-action-primary) 8%, var(--color-bg-surface));
        }
        .cue:disabled { color: var(--color-text-muted); background: var(--color-bg-card); cursor: not-allowed; opacity: 0.62; }
        .cue__copy { display: grid; gap: 4px; min-width: 0; }
        .cue__label { font-size: 11px; font-weight: 800; letter-spacing: 0.14em; }
        .cue__detail { overflow: hidden; color: var(--color-text-secondary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
        .badge {
          justify-self: start;
          padding: 3px 8px;
          border-radius: 6px;
          color: var(--audio-action-foreground);
          background: var(--color-action-primary);
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 0.12em;
        }
        .cue__meta { display: flex; align-items: center; gap: 8px; }
        .cue__duration {
          color: var(--color-text-muted);
          font-family: var(--font-mono);
          font-size: 11px;
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }
        .cue__play {
          display: grid;
          place-items: center;
          flex: 0 0 44px;
          width: 44px;
          height: 44px;
          border-radius: 12px;
          color: var(--audio-action-foreground);
          background: var(--color-action-primary);
          font-size: 14px;
        }
        .cue:disabled .cue__play { color: var(--color-text-muted); background: var(--color-action-disabled); }
        button:focus-visible, input:focus-visible { outline: 3px solid var(--color-focus-ring); outline-offset: 2px; }
        @media (min-width: 640px) {
          .main { padding: 24px; }
          .cue-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .frame--fullscreen .main { width: min(100%, 720px); margin: 0 auto; }
        }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
        }
      </style>
      <${frameTag} class="${frameClass}" role="dialog" aria-modal="true" aria-labelledby="audio-sampler-title">
        <div class="screen">
          <header class="topbar">
            <div>
              <p class="eyebrow">HIIT FIT</p>
              <h1 id="audio-sampler-title">Audio samples</h1>
            </div>
            <button class="close" type="button" aria-label="Close audio samples">×</button>
          </header>
          <main class="main">
            <div class="intro">
              <p>Set your cue volume, then tap any sound to preview it. Starting another preview stops the current one.</p>
              <span class="status" data-state="idle" role="status" aria-live="polite">NOT READY</span>
            </div>
            <section class="volume-card" aria-labelledby="volume-label">
              <div class="volume-row">
                <span class="section-label" id="volume-label">Cue volume</span>
                <output class="volume-value" for="volume">${getVolume()}</output>
              </div>
              <input id="volume" type="range" min="0" max="100" value="${getVolume()}" aria-labelledby="volume-label">
              <button class="enable" type="button">Enable audio</button>
              <p class="error" hidden></p>
            </section>
            <section aria-labelledby="sounds-title">
              <div class="sounds-head">
                <span class="section-label" id="sounds-title">Sound library</span>
                <span class="sounds-hint">Tap to preview</span>
              </div>
              <div class="cue-grid">${cueMarkup}</div>
            </section>
          </main>
        </div>
      </${frameTag}>
    `;
  }

  bindEvents() {
    this.shadowRoot.querySelector(".close").addEventListener("click", () => this.close());
    this.shadowRoot.querySelector(".enable").addEventListener("click", () => void this.prepareAudio());
    this.shadowRoot.querySelector("#volume").addEventListener("input", (event) => {
      setVolume(event.target.value);
      this.shadowRoot.querySelector(".volume-value").value = getVolume();
      this.dispatchEvent(new CustomEvent("audio-sampler-volume", {
        bubbles: true,
        detail: { volume: getVolume() },
      }));
    });
    this.shadowRoot.querySelectorAll(".cue").forEach((button) => {
      button.addEventListener("click", () => void this.preview(button.dataset.event));
    });
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog?.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
  }

  async preview(eventName) {
    if (!this._ready) return;
    await resumeAudioContext();
    const timing = playTimerEvent(eventName);
    window.clearTimeout(this._previewTimer);
    this.shadowRoot.querySelectorAll(".cue").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.event === eventName));
    });
    const cue = CUES.find((item) => item.event === eventName);
    this.setStatus("playing", `PLAYING · ${cue.label}`);
    this.dispatchEvent(new CustomEvent("audio-sampler-preview", {
      bubbles: true,
      detail: { eventName, duration: timing.duration },
    }));
    this._previewTimer = window.setTimeout(() => {
      this.shadowRoot.querySelector(`[data-event="${eventName}"]`)?.setAttribute("aria-pressed", "false");
      this.setStatus("ready", "READY");
    }, timing.duration * 1000);
  }

  updateDurations() {
    CUES.forEach((cue) => {
      const duration = getCueDuration(cue.event);
      const output = this.shadowRoot.querySelector(`[data-duration="${cue.event}"]`);
      output.textContent = `${duration.toFixed(duration < 10 ? 1 : 0)}s`;
    });
  }

  updateState() {
    if (!this.shadowRoot?.querySelector(".status")) return;
    const enable = this.shadowRoot.querySelector(".enable");
    const error = this.shadowRoot.querySelector(".error");
    enable.disabled = this._loading;
    enable.hidden = this._ready;
    enable.textContent = this._loading ? "Loading audio…" : "Enable audio";
    error.hidden = !this._error;
    error.textContent = this._error;
    this.shadowRoot.querySelectorAll(".cue").forEach((button) => {
      button.disabled = !this._ready;
    });
    if (this._error) {
      this.setStatus("error", "ERROR");
    } else if (this._loading) {
      this.setStatus("loading", "LOADING");
    } else if (this._ready) {
      this.setStatus("ready", "READY");
    } else {
      this.setStatus("idle", "NOT READY");
    }
  }

  setStatus(state, text) {
    const status = this.shadowRoot?.querySelector(".status");
    if (!status) return;
    status.dataset.state = state;
    status.textContent = text;
    status.title = text;
  }
}

if (!customElements.get("hiit-audio-sampler")) {
  customElements.define("hiit-audio-sampler", HiitAudioSampler);
}

export function openAudioSampler({ mode = "dialog" } = {}) {
  if (!new Set(["dialog", "fullscreen"]).has(mode)) {
    throw new RangeError('mode must be "dialog" or "fullscreen"');
  }
  document.querySelector("hiit-audio-sampler")?.close();
  const opener = document.activeElement;
  const sampler = document.createElement("hiit-audio-sampler");
  sampler.setAttribute("mode", mode);
  sampler.addEventListener("audio-sampler-close", () => opener?.focus(), { once: true });
  document.body.append(sampler);
  void sampler.prepareAudio();
  return sampler;
}
