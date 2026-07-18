const ASSET_URLS = {
  intro: new URL("./u_7xr5ffk4oq-opening-bell-421471.mp3", import.meta.url),
  countdownBell: new URL("./servant-bell-ring-2-211683.mp3", import.meta.url),
  startBlock: new URL("./universfield-male-voice-letx27s-go-352481.mp3", import.meta.url),
  startActivity: new URL("./gooo-83817.mp3", import.meta.url),
  endActivity: new URL("./11325622-female-vocal-321-countdown-240912.mp3", import.meta.url),
  startRest: new URL("./freesound_community-woo-hoo-82843.mp3", import.meta.url),
  endBlock: new URL("./freesound_community-yay-6326.mp3", import.meta.url),
  endProgramme: new URL("./freesound_community-well-done-judas-20354.mp3", import.meta.url),
  postProgramme: new URL("./44702__sandyrb__you-go-girl-01.wav", import.meta.url),
};

const END_PROGRAMME_SECONDS = 22;
const COUNTDOWN_SECONDS = 3;
const FADE_OUT_SECONDS = 0.05;

// The programme-end event is the only stacked cue. To append another file,
// add it to ASSET_URLS above and add one entry here. Items play sequentially.
const END_PROGRAMME_QUEUE = Object.freeze([
  Object.freeze({ asset: "endProgramme", maxDuration: END_PROGRAMME_SECONDS }),
  Object.freeze({ asset: "postProgramme" }),
]);

let audioCtx = null;
let masterGain = null;
let volume = 80;
let bootPromise = null;

const buffers = new Map();
const cappedBuffers = new Map();
const activeSources = new Map();

// Fetching starts when the module loads. Decoding waits for the user gesture
// that creates the AudioContext.
const assetDataPromises = new Map(
  Object.entries(ASSET_URLS).map(([name, url]) => [name, fetch(url).then((response) => {
    if (!response.ok) {
      throw new Error(`Could not load ${url.pathname}: ${response.status} ${response.statusText}`);
    }
    return response.arrayBuffer();
  })]),
);

export function bootAudioContext() {
  if (bootPromise) return bootPromise;

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return Promise.reject(new Error("This browser does not support the Web Audio API."));
  }

  audioCtx = new AudioContextClass();
  masterGain = audioCtx.createGain();
  masterGain.gain.value = volumeToGain(volume);
  masterGain.connect(audioCtx.destination);

  bootPromise = Promise.all([...assetDataPromises].map(async ([name, dataPromise]) => {
    const data = await dataPromise;
    buffers.set(name, await audioCtx.decodeAudioData(data.slice(0)));
  })).then(() => audioCtx);

  return bootPromise;
}

export function resumeAudioContext() {
  if (!audioCtx) return Promise.resolve();
  return audioCtx.state === "suspended" ? audioCtx.resume() : Promise.resolve();
}

export function setVolume(v) {
  volume = clamp(Number(v) || 0, 0, 100);
  if (masterGain) {
    masterGain.gain.setValueAtTime(volumeToGain(volume), audioCtx.currentTime);
  }
}

export function getVolume() {
  return volume;
}

// Original integration API retained for drop-in compatibility.
export function playIntroChime(t0 = 0) {
  scheduleSingleBuffer("intro", t0);
}

export function playCountdownTick(t0 = 0) {
  scheduleSingleBuffer("countdownBell", t0);
}

export function playStartActivity(t0 = 0) {
  scheduleSemanticCue("startActivity", scheduledTime(t0));
}

export function playEndActivity(t0 = 0) {
  scheduleSemanticCue("endActivity", scheduledTime(t0));
}

export function playEndBlock(t0 = 0) {
  scheduleSemanticCue("endBlock", scheduledTime(t0));
}

export function playEndProgramme(t0 = 0) {
  scheduleSemanticCue("endProgramme", scheduledTime(t0));
}

export function playPostProgramme(t0 = 0) {
  scheduleSemanticCue("postProgramme", scheduledTime(t0));
}

// Timer-facing start trigger. The application owns phase boundaries and can
// subtract getCueDuration(eventName) when a cue must finish on a boundary.
export function playTimerEvent(eventName, startIn = 0) {
  assertBooted();
  resumeIfSuspended();

  const cue = normalizeCueName(eventName);
  const startOffset = Number(startIn);
  if (!Number.isFinite(startOffset) || startOffset < 0) {
    throw new TypeError("startIn must be a non-negative number of seconds");
  }

  const startTime = scheduledTime(startOffset);
  scheduleSemanticCue(cue, startTime);
  return {
    cue,
    startTime,
    duration: getCueDuration(cue),
  };
}

// Extended semantic API for the complete timer sequence.
export function playProgrammeStart(t0 = 0) {
  scheduleSemanticCue("programmeStart", scheduledTime(t0));
}

export function playStartBlock(t0 = 0) {
  scheduleSemanticCue("startBlock", scheduledTime(t0));
}

export function playStartRest(t0 = 0) {
  scheduleSemanticCue("startRest", scheduledTime(t0));
}

export function playEndRest(t0 = 0) {
  scheduleSemanticCue("endRest", scheduledTime(t0), COUNTDOWN_SECONDS);
}

export function stopAllCues(t0 = 0) {
  assertBooted();
  resumeIfSuspended();
  stopActiveSourcesAt(scheduledTime(t0));
}

// Timer lifecycle helpers. Pausing freezes the AudioContext clock, preserving
// the exact playback position of an active cue and every future cue offset.
// Terminating invalidates the current cue and all scheduled starts.
export function pauseTimerAudio() {
  if (!audioCtx || audioCtx.state !== "running") return Promise.resolve();
  return audioCtx.suspend();
}

export function resumeTimerAudio() {
  return resumeAudioContext();
}

export function terminateTimerAudio() {
  cancelScheduledCues();
}

export function syncTimerAudio(events, t0 = 0) {
  cancelScheduledCues();
  return scheduleCueSequence(events, t0);
}

export function cancelScheduledCues() {
  if (!audioCtx) return;
  stopActiveSourcesAt(audioCtx.currentTime);
}

export function getCueDuration(cueName) {
  assertBooted();
  const cue = normalizeCueName(cueName);
  if (cue === "programmeStart") return buffers.get("intro").duration;
  if (cue === "endRest") return COUNTDOWN_SECONDS;
  if (cue === "endProgramme") return getBufferQueueDuration(END_PROGRAMME_QUEUE);
  return buffers.get(cue).duration;
}

// Schedules start triggers against one AudioContext timestamp. The application
// calculates each event's start offset, using getCueDuration() when needed.
export function scheduleCueSequence(events, t0 = 0) {
  assertBooted();
  resumeIfSuspended();

  if (!Array.isArray(events) || events.length === 0) {
    throw new TypeError("events must be a non-empty array");
  }

  const baseTime = scheduledTime(t0);
  const sortedEvents = events.map((event, index) => {
    const at = Number(event?.at);
    if (!event || !Number.isFinite(at) || at < 0) {
      throw new TypeError(`events[${index}] must have a non-negative numeric at value`);
    }
    return { cue: normalizeCueName(event.cue), at };
  }).sort((a, b) => a.at - b.at);

  for (let i = 1; i < sortedEvents.length; i += 1) {
    if (sortedEvents[i].at <= sortedEvents[i - 1].at) {
      throw new RangeError("audio start times must be strictly increasing");
    }
  }

  let endOffset = 0;
  sortedEvents.forEach((event, index) => {
    const nextEvent = sortedEvents[index + 1];
    const windowSeconds = nextEvent ? nextEvent.at - event.at : undefined;
    scheduleSemanticCue(event.cue, baseTime + event.at, windowSeconds);
    const scheduledDuration = minimumDefined(getCueDuration(event.cue), windowSeconds);
    endOffset = Math.max(endOffset, event.at + scheduledDuration);
  });

  return {
    startTime: baseTime,
    endTime: baseTime + endOffset,
    events: sortedEvents.map((event) => ({
      cue: event.cue,
      startTime: baseTime + event.at,
      duration: getCueDuration(event.cue),
    })),
  };
}

function scheduleSemanticCue(cue, startAt, windowSeconds) {
  assertBooted();
  resumeIfSuspended();
  stopActiveSourcesAt(startAt);

  const maxDuration = windowSeconds;

  if (cue === "endProgramme") {
    scheduleBufferQueueAt(END_PROGRAMME_QUEUE, startAt, windowSeconds);
    return;
  }

  if (cue === "programmeStart") {
    scheduleBufferAt("intro", startAt, maxDuration);
    return;
  }

  if (cue === "endRest") {
    const duration = minimumDefined(maxDuration, COUNTDOWN_SECONDS);
    for (let i = 0; i < COUNTDOWN_SECONDS && i < duration; i += 1) {
      scheduleBeepAt(startAt + i);
    }
    return;
  }

  scheduleBufferAt(cue, startAt, maxDuration);
}

function scheduleSingleBuffer(name, t0) {
  assertBooted();
  resumeIfSuspended();
  const startAt = scheduledTime(t0);
  stopActiveSourcesAt(startAt);
  scheduleBufferAt(name, startAt);
}

function scheduleBufferAt(name, startAt, maxDuration) {
  const buffer = getCappedBuffer(name, maxDuration);
  const source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(masterGain);
  registerSource(source, startAt + buffer.duration);
  source.start(startAt);
}

function scheduleBufferQueueAt(queue, startAt, maxDuration) {
  let cursor = startAt;
  let remaining = Number.isFinite(maxDuration) ? maxDuration : Infinity;

  for (const item of queue) {
    if (remaining <= 0) break;
    const buffer = buffers.get(item.asset);
    const itemDuration = Math.min(
      buffer.duration,
      Number.isFinite(item.maxDuration) ? item.maxDuration : Infinity,
      remaining,
    );
    if (itemDuration <= 0) continue;
    scheduleBufferAt(item.asset, cursor, itemDuration);
    cursor += itemDuration;
    remaining -= itemDuration;
  }

  return cursor - startAt;
}

function getBufferQueueDuration(queue) {
  return queue.reduce((total, item) => {
    const buffer = buffers.get(item.asset);
    return total + Math.min(
      buffer.duration,
      Number.isFinite(item.maxDuration) ? item.maxDuration : Infinity,
    );
  }, 0);
}

function scheduleBeepAt(startAt) {
  const oscillator = audioCtx.createOscillator();
  const envelope = audioCtx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(1250, startAt);
  envelope.gain.setValueAtTime(0.0001, startAt);
  envelope.gain.linearRampToValueAtTime(0.65, startAt + 0.003);
  envelope.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.09);
  oscillator.connect(envelope);
  envelope.connect(masterGain);
  registerSource(oscillator, startAt + 0.1);
  oscillator.start(startAt);
  oscillator.stop(startAt + 0.1);
}

function getCappedBuffer(name, maxDuration) {
  const sourceBuffer = buffers.get(name);
  if (!sourceBuffer) {
    throw new Error(`Audio cue "${name}" is unavailable. Await bootAudioContext().`);
  }

  if (!Number.isFinite(maxDuration) || maxDuration <= 0 || sourceBuffer.duration <= maxDuration) {
    return sourceBuffer;
  }

  const duration = Math.max(0.001, maxDuration);
  const cacheKey = `${name}:${duration.toFixed(4)}`;
  if (cappedBuffers.has(cacheKey)) return cappedBuffers.get(cacheKey);

  const frameCount = Math.max(1, Math.floor(duration * sourceBuffer.sampleRate));
  const capped = audioCtx.createBuffer(
    sourceBuffer.numberOfChannels,
    frameCount,
    sourceBuffer.sampleRate,
  );
  const fadeFrames = Math.min(frameCount, Math.floor(FADE_OUT_SECONDS * sourceBuffer.sampleRate));

  for (let channel = 0; channel < sourceBuffer.numberOfChannels; channel += 1) {
    const sourceData = sourceBuffer.getChannelData(channel);
    const targetData = capped.getChannelData(channel);
    targetData.set(sourceData.subarray(0, frameCount));
    for (let i = 0; i < fadeFrames; i += 1) {
      targetData[frameCount - fadeFrames + i] *= 1 - (i / fadeFrames);
    }
  }

  cappedBuffers.set(cacheKey, capped);
  return capped;
}

function registerSource(source, scheduledStop) {
  activeSources.set(source, scheduledStop);
  source.addEventListener("ended", () => activeSources.delete(source), { once: true });
}

function stopActiveSourcesAt(stopAt) {
  for (const [source, scheduledStop] of activeSources) {
    if (stopAt < scheduledStop) {
      source.stop(stopAt);
      activeSources.set(source, stopAt);
    }
  }
}

function normalizeCueName(cueName) {
  const aliases = {
    programStart: "programmeStart",
    programEnd: "endProgramme",
    programmeEnd: "endProgramme",
    blockStart: "startBlock",
    activityStart: "startActivity",
    activityEnd: "endActivity",
    restStart: "startRest",
    restEnd: "endRest",
    blockEnd: "endBlock",
  };
  const cue = aliases[cueName] || cueName;
  const validCues = [
    "programmeStart", "startBlock", "startActivity", "endActivity",
    "startRest", "endRest", "endBlock", "endProgramme", "postProgramme",
  ];
  if (!validCues.includes(cue)) throw new RangeError(`Unknown cue: ${cueName}`);
  return cue;
}

function assertBooted() {
  if (!audioCtx || !masterGain || buffers.size !== assetDataPromises.size) {
    throw new Error("Await bootAudioContext() before scheduling cues.");
  }
}

function resumeIfSuspended() {
  if (audioCtx.state === "suspended") void audioCtx.resume();
}

function scheduledTime(t0) {
  assertBooted();
  return audioCtx.currentTime + Math.max(0, Number(t0) || 0);
}

function minimumDefined(a, b) {
  if (!Number.isFinite(a)) return b;
  if (!Number.isFinite(b)) return a;
  return Math.min(a, b);
}

function volumeToGain(value) {
  return value * 0.025;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
