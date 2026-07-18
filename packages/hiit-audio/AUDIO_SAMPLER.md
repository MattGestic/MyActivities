# HIIT FIT audio package

This package contains a framework-free Web Component for previewing the HIIT FIT cues and a timer-facing Web Audio engine for playing them in an application. The sampler can open as a modal dialog or a full-screen layer and inherits RepStack theme tokens from its host page.

## Package contents

Keep these files together unless you also update the asset paths at the top of `audioEngine.js`:

- `audioEngine.js` — loads, decodes, schedules, pauses, resumes, and stops cues.
- `audioSampler.js` — defines `<hiit-audio-sampler>` and the launcher helper.
- `index.html` — working dark/light integration example.
- The bundled `.mp3` and `.wav` files — cue assets resolved relative to `audioEngine.js`.

The files use browser ES modules and fetch audio assets, so serve them through HTTP rather than opening `index.html` with a `file://` URL.

## Quick start

Copy the package into a public/static directory that your application serves, then import the sampler once:

```js
import { openAudioSampler } from "/audio/audioSampler.js";

document.querySelector("#audio-settings").addEventListener("click", () => {
  openAudioSampler({ mode: "dialog" });
});
```

Use `mode: "fullscreen"` when the sampler should occupy the whole viewport:

```js
openAudioSampler({ mode: "fullscreen" });
```

`openAudioSampler()` returns the created component. It closes any existing sampler, prepares audio from the user's button gesture, stops previews when closed, removes itself from the DOM, and restores focus to the opening control.

## Server-rendered applications

`audioSampler.js` registers a custom element and therefore must be imported in the browser, not during server rendering. A client-side dynamic import is sufficient:

```js
async function showAudioSettings() {
  const { openAudioSampler } = await import("/audio/audioSampler.js");
  openAudioSampler({ mode: "dialog" });
}
```

Call that function from a real click or tap. Browsers commonly require a user gesture before an `AudioContext` may start.

## Direct component use

Import `audioSampler.js` once and create the custom element yourself when the application needs to retain its reference:

```js
import "/audio/audioSampler.js";

const sampler = document.createElement("hiit-audio-sampler");
sampler.setAttribute("mode", "fullscreen");
document.body.append(sampler);

// Call from a user gesture. Otherwise the screen offers an Enable audio button.
await sampler.prepareAudio();

// Later:
sampler.close();
```

Supported modes are `dialog` and `fullscreen`. The default is `dialog`.

## Sampler events

All sampler events bubble, so an application may listen on the component or a parent element.

| Event | `detail` | When it fires |
| --- | --- | --- |
| `audio-sampler-ready` | none | All audio files have loaded and decoded. |
| `audio-sampler-volume` | `{ volume }` | The user changes the 0–100 volume slider. |
| `audio-sampler-preview` | `{ eventName, duration }` | A preview begins. |
| `audio-sampler-close` | none | The sampler closes and is about to be removed. |

Example:

```js
const sampler = openAudioSampler({ mode: "dialog" });

sampler.addEventListener("audio-sampler-volume", (event) => {
  saveAudioPreference(event.detail.volume);
});
```

The status indicator has a fixed 148 px footprint. Long playing labels are visually truncated with an ellipsis and exposed in full through the element's accessible status text and `title`, so preview changes do not reflow the screen.

## Initialize the timer audio engine

The timer engine must finish loading before duration or playback functions are used. Initialize it from the same gesture that starts the workout or enables sound:

```js
import {
  bootAudioContext,
  getCueDuration,
  playTimerEvent,
  setVolume,
} from "/audio/audioEngine.js";

startButton.addEventListener("click", async () => {
  await bootAudioContext();
  setVolume(80);
  startWorkout();
});
```

`setVolume(value)` accepts a value from 0 to 100. `getVolume()` returns the current value.

## Cue names

Use the names in the first column with `getCueDuration()`, `playTimerEvent()`, or `scheduleCueSequence()`.

| Timer event | Sound |
| --- | --- |
| `programmeStart` | Opening bell |
| `blockStart` | Male voice: “Let's go!” |
| `activityStart` | “Gooo” |
| `activityEnd` | Female voice: “3, 2, 1” |
| `restStart` | “Woohoo” |
| `restEnd` | Three short beeps over three seconds |
| `blockEnd` | “Yay” |
| `programmeEnd` | “Well done” capped and faded at 22 seconds, then the WAV queue item |
| `postProgramme` | The WAV “You go girl” queue item by itself |

The engine also accepts `programStart` and `programEnd` spellings. If a block start and its first activity start occur at the same boundary, select the single cue the product should play; do not schedule two cues at the same timestamp.

## Start-aligned cues

For sounds that begin at a timer boundary, call the start trigger at that boundary or provide a future offset in seconds:

```js
playTimerEvent("blockStart");       // now
playTimerEvent("activityStart", 5); // five seconds from now
```

The return value contains the normalized cue name, AudioContext start time, and decoded duration.

## End-aligned cues

The application remains the timer authority. To make a sound finish at a phase boundary, subtract its decoded duration from the time remaining and schedule that start offset:

```js
const boundaryIn = timer.secondsRemaining;
const duration = getCueDuration("activityEnd");
const startIn = boundaryIn - duration;

if (startIn >= 0) {
  playTimerEvent("activityEnd", startIn);
} else {
  // Product decision: skip this cue or choose a shorter fallback.
}
```

Do not pass a negative offset. For the best timing, schedule against the audio clock as soon as the phase begins rather than waiting for a JavaScript timeout near the boundary.

## Schedule a complete sequence

`scheduleCueSequence(events, t0)` schedules strictly increasing start offsets against one AudioContext timestamp. Every cue is automatically capped at the next cue start so sounds cannot overlap into the following timer event.

```js
import {
  getCueDuration,
  scheduleCueSequence,
} from "/audio/audioEngine.js";

const activityStartsAt = 10;
const activityEndsAt = 50;
const restEndsAt = 60;

scheduleCueSequence([
  { cue: "programmeStart", at: 0 },
  { cue: "blockStart", at: activityStartsAt },
  {
    cue: "activityEnd",
    at: activityEndsAt - getCueDuration("activityEnd"),
  },
  { cue: "restStart", at: activityEndsAt },
  {
    cue: "restEnd",
    at: restEndsAt - getCueDuration("restEnd"),
  },
  { cue: "activityStart", at: restEndsAt },
]);
```

Offsets must be non-negative and unique. Build the array after the engine has initialized so decoded durations are available.

## Pause, resume, terminate, and resync

Pause the application timer and audio in the same interaction. `pauseTimerAudio()` freezes the AudioContext clock, which preserves both an active sound's playback position and every future scheduled offset. `resumeTimerAudio()` continues from that exact point.

```js
import {
  pauseTimerAudio,
  resumeTimerAudio,
  syncTimerAudio,
  terminateTimerAudio,
} from "/audio/audioEngine.js";

function pauseWorkout() {
  timer.pause();
  void pauseTimerAudio();
}

function resumeWorkout() {
  timer.resume();
  void resumeTimerAudio();
}

function terminateWorkout() {
  timer.terminate();
  terminateTimerAudio();
}
```

If the application changes the interval structure while paused or restores a timer from persisted state, calculate a new array of future cue starts from the timer's authoritative remaining state and replace the old schedule:

```js
syncTimerAudio(buildCueStarts(timer.remaining));
```

`cancelScheduledCues()` removes the active and future cues without changing timer state. `stopAllCues(t0)` can stop them at a future offset.

## Programme-end queue

`programmeEnd` is the only cue that stacks audio files. Its ordered queue is defined by `END_PROGRAMME_QUEUE` near the top of `audioEngine.js`:

```js
const END_PROGRAMME_QUEUE = Object.freeze([
  Object.freeze({ asset: "endProgramme", maxDuration: 22 }),
  Object.freeze({ asset: "postProgramme" }),
]);
```

Each item begins when the previous item finishes. To add or reorder end-of-programme sounds, add the asset URL to `ASSET_URLS` and edit this queue. Other timer events intentionally accept one cue only.

## Theme integration

The component's Shadow DOM consumes the RepStack `--color-*` and `--font-*` custom properties from the host document. Define those variables at the application root and toggle `data-theme="dark"` or `data-theme="light"` on an ancestor. The included `index.html` contains a complete working dark/light token example.

The primary variables used are:

- Backgrounds: `--color-bg-app`, `--color-bg-surface`, `--color-bg-card`, `--color-bg-card-elevated`
- Text: `--color-text-primary`, `--color-text-secondary`, `--color-text-muted`
- Actions and state: `--color-action-primary`, `--color-action-primary-hover`, `--color-action-primary-pressed`, `--color-action-disabled`, `--color-danger`, `--color-focus-ring`
- Structure: `--color-border-subtle`
- Type: `--font-body`, `--font-display`, `--font-mono`

## Integration checklist

1. Copy the JavaScript modules and every referenced audio asset into a publicly served directory.
2. Preserve their relative paths or update `ASSET_URLS`.
3. Import the sampler only on the client in server-rendered applications.
4. Initialize audio from a click or tap before calling duration or playback APIs.
5. Let the application countdown own all boundaries; subtract decoded cue durations for end-aligned sounds.
6. Call the audio pause, resume, and terminate helpers with the matching timer lifecycle actions.
7. Define the RepStack theme tokens on the host page.
8. Test the packaged files through HTTP on the browsers and devices supported by the application.
