(() => {
  'use strict';

  const SAMPLE_INTERVAL_MS = 50;
  const CHART_INTERVAL_MS = 100;
  const WINDOW_SECONDS = 30;
  const $ = (id) => document.getElementById(id);
  const startButton = $('startButton');
  const stopButton = $('stopButton');
  const exportButton = $('exportButton');
  const clearButton = $('clearButton');
  const status = $('status');
  const statusText = $('statusText');
  const sampleRateElement = $('sampleRate');
  const durationElement = $('duration');
  const sampleCountElement = $('sampleCount');
  const errorElement = $('errorMessage');

  let sensor = null;
  let sensorType = null;
  let latest = { x: 0, y: 0, z: 0, alpha: null, beta: null, gamma: null };
  let recording = false;
  let startedAt = 0;
  let recordingTimestamp = '';
  let sampleTimer = null;
  let chartTimer = null;
  let samples = [];
  let chart = null;
  let sensorFailure = null;
  let firstSensorValue = false;

  function setStatus(state, label) {
    status.className = `status status-${state}`;
    statusText.textContent = label;
  }

  function showError(message, allowRetry = false) {
    errorElement.replaceChildren(document.createTextNode(message));
    if (allowRetry) {
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'button';
      retry.textContent = 'Retry permission';
      retry.addEventListener('click', startRecording, { once: true });
      errorElement.append(document.createTextNode(' '), retry);
    }
    errorElement.hidden = false;
  }

  function clearError() {
    errorElement.hidden = true;
    errorElement.replaceChildren();
  }

  function makeChart() {
    if (typeof window.Chart !== 'function') {
      showError('Chart.js could not be loaded. Check your internet connection and reload the page.');
      return;
    }
    const ctx = $('sensorChart').getContext('2d');
    chart = new window.Chart(ctx, {
      type: 'line',
      data: {
        datasets: [
          { label: 'X', data: [], borderColor: '#ff5c67', backgroundColor: '#ff5c67', pointRadius: 0, borderWidth: 1.6, tension: 0.12 },
          { label: 'Y', data: [], borderColor: '#54d68b', backgroundColor: '#54d68b', pointRadius: 0, borderWidth: 1.6, tension: 0.12 },
          { label: 'Z', data: [], borderColor: '#59a6ff', backgroundColor: '#59a6ff', pointRadius: 0, borderWidth: 1.6, tension: 0.12 }
        ]
      },
      options: {
        animation: false, responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false } },
        scales: {
          x: { type: 'linear', title: { display: true, text: 'Time (seconds)', color: '#aab5c2' }, ticks: { color: '#8997a7' }, grid: { color: '#2a333e' } },
          y: { title: { display: true, text: 'Sensor value', color: '#aab5c2' }, ticks: { color: '#8997a7' }, grid: { color: '#2a333e' } }
        }
      }
    });
  }

  function latestValues() {
    return {
      x: Number.isFinite(latest.x) ? latest.x : 0,
      y: Number.isFinite(latest.y) ? latest.y : 0,
      z: Number.isFinite(latest.z) ? latest.z : 0,
      alpha: Number.isFinite(latest.alpha) ? latest.alpha : 0,
      beta: Number.isFinite(latest.beta) ? latest.beta : 0,
      gamma: Number.isFinite(latest.gamma) ? latest.gamma : 0
    };
  }

  function recordSample() {
    if (!recording) return;
    const t = (performance.now() - startedAt) / 1000;
    samples.push({ t, ...latestValues() });
    sampleCountElement.textContent = String(samples.length);
  }

  function updateChart() {
    if (!chart) return;
    const elapsed = recording ? (performance.now() - startedAt) / 1000 : (samples.length ? samples[samples.length - 1].t : 0);
    const visible = samples.filter((sample) => sample.t >= Math.max(0, elapsed - WINDOW_SECONDS));
    chart.data.datasets.forEach((dataset, index) => {
      const key = ['x', 'y', 'z'][index];
      dataset.data = visible.map((sample) => ({ x: sample.t, y: sample[key] }));
    });
    chart.options.scales.x.min = Math.max(0, elapsed - WINDOW_SECONDS);
    chart.options.scales.x.max = Math.max(WINDOW_SECONDS, elapsed);
    chart.update('none');
  }

  function updateDuration() {
    const seconds = recording ? (performance.now() - startedAt) / 1000 : (samples.length ? samples[samples.length - 1].t : 0);
    const minutes = Math.floor(seconds / 60);
    durationElement.textContent = `${String(minutes).padStart(2, '0')}:${(seconds % 60).toFixed(1).padStart(4, '0')}`;
  }

  function readSensor() {
    if (!window.isSecureContext) throw new Error('Sensor access requires HTTPS or localhost. Open this page over a secure connection.');
    if ('Magnetometer' in window) {
      try {
        sensor = new Magnetometer({ frequency: 20 });
        sensor.addEventListener('reading', () => {
          latest = { x: sensor.x, y: sensor.y, z: sensor.z, alpha: null, beta: null, gamma: null };
          firstSensorValue = true;
        });
        sensor.addEventListener('error', (event) => {
          sensorFailure = event.error;
          if (recording) stopRecording();
          const denied = event.error && event.error.name === 'NotAllowedError';
          setStatus(denied ? 'permission' : 'error', denied ? 'Permission Needed' : 'Idle');
          showError(denied ? 'Magnetometer permission was denied. Allow motion sensors in browser settings, then retry.' : `Magnetometer stopped: ${event.error?.message || 'sensor error'}. Try another supported browser.`, denied);
        });
        sensor.start();
        sensorType = 'magnetometer';
        return true;
      } catch (error) {
        sensor = null;
        if (error && error.name === 'NotAllowedError') throw error;
        sensorFailure = error;
      }
    }
    return startOrientationSensor();
  }

  function startOrientationSensor() {
    if (!('DeviceOrientationEvent' in window)) return Promise.resolve(false);
    const attachListener = () => {
    const handler = (event) => {
      if (event.alpha === null && event.beta === null && event.gamma === null) return;
      latest = { x: event.beta ?? 0, y: event.gamma ?? 0, z: event.alpha ?? 0, alpha: event.alpha, beta: event.beta, gamma: event.gamma };
      firstSensorValue = true;
    };
    window.addEventListener('deviceorientation', handler);
    sensor = { stop: () => window.removeEventListener('deviceorientation', handler) };
    sensorType = 'device_orientation';
    return true;
    };
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {
      return DeviceOrientationEvent.requestPermission().then((result) => {
        if (result !== 'granted') {
          const denied = new Error('Orientation permission was not granted.');
          denied.name = 'NotAllowedError';
          throw denied;
        }
        return attachListener();
      });
    }
    return Promise.resolve(attachListener());
  }

  async function startRecording() {
    if (recording) return;
    clearError();
    setStatus('permission', 'Permission Needed');
    startButton.disabled = true;
    try {
      let available;
      if ('Magnetometer' in window) {
        try {
          available = readSensor();
          if (available && typeof available.then === 'function') available = await available;
        } catch (error) {
          if (error.name === 'NotAllowedError') throw error;
          available = await startOrientationSensor();
        }
      } else {
        // Invoked synchronously within this click handler to preserve iOS user activation.
        available = await startOrientationSensor();
      }
      if (!available) throw new Error('No supported motion sensor is available. Try current Chrome on Android or Safari on iOS, and confirm the device has motion sensors.');
      samples = [];
      firstSensorValue = false;
      recordingTimestamp = new Date().toISOString();
      startedAt = performance.now();
      firstSensorValue = sensorType === 'magnetometer';
      recording = true;
      sampleRateElement.textContent = '20 Hz';
      sampleCountElement.textContent = '0';
      durationElement.textContent = '00:00.0';
      startButton.disabled = true;
      stopButton.disabled = false;
      exportButton.disabled = true;
      setStatus('recording', 'Recording');
      recordSample();
      sampleTimer = window.setInterval(recordSample, SAMPLE_INTERVAL_MS);
      chartTimer = window.setInterval(() => {
        updateChart();
        updateDuration();
        if (!firstSensorValue && performance.now() - startedAt > 2000) {
          showError('The sensor started but is not providing readings. Check browser sensor permissions or try a different browser.');
        }
      }, CHART_INTERVAL_MS);
    } catch (error) {
      sensor = null;
      startButton.disabled = false;
      const denied = error && (error.name === 'NotAllowedError' || /permission/i.test(error.message));
      setStatus(denied ? 'permission' : 'idle', denied ? 'Permission Needed' : 'Idle');
      showError(error?.message || 'Could not start sensor recording. Please try again.', denied);
    }
  }

  function stopRecording() {
    if (!recording) return;
    recording = false;
    window.clearInterval(sampleTimer);
    window.clearInterval(chartTimer);
    sampleTimer = null;
    chartTimer = null;
    if (sensor && typeof sensor.stop === 'function') {
      try { sensor.stop(); } catch (error) { showError(`Sensor stopped with a warning: ${error.message}`); }
    }
    sensor = null;
    updateDuration();
    updateChart();
    startButton.disabled = false;
    stopButton.disabled = true;
    exportButton.disabled = samples.length === 0;
    setStatus('idle', 'Idle');
    if (sensorFailure) {
      showError(`Recording ended because the sensor became unavailable: ${sensorFailure.message || 'sensor error'}. You can restart recording.`);
      sensorFailure = null;
    }
  }

  function exportJSON() {
    if (!samples.length) {
      showError('There are no recorded samples to export. Start and stop a recording first.');
      return;
    }
    const duration = samples[samples.length - 1].t;
    const recordingData = {
      metadata: {
        timestamp: recordingTimestamp,
        duration_seconds: duration,
        sample_rate_hz: duration > 0 ? samples.length / duration : 20,
        sensor_type: sensorType || 'device_orientation',
        device_info: `${navigator.userAgent} | ${navigator.platform || 'unknown platform'}`
      },
      samples
    };
    const blob = new Blob([JSON.stringify(recordingData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `magnetometer-recording-${new Date(recordingTimestamp).toISOString().replace(/[:.]/g, '-')}.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function clearChart() {
    if (recording) {
      showError('Stop the recording before clearing its chart.');
      return;
    }
    samples = [];
    sampleCountElement.textContent = '0';
    durationElement.textContent = '00:00.0';
    exportButton.disabled = true;
    clearError();
    updateChart();
  }

  startButton.addEventListener('click', startRecording);
  stopButton.addEventListener('click', stopRecording);
  exportButton.addEventListener('click', exportJSON);
  clearButton.addEventListener('click', clearChart);
  makeChart();
})();
