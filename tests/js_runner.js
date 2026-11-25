'use strict';
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
global.APP_PROTOCOL = { SYNC_HEADER: [1,0,1,0,1,0,1,0], END_OF_MESSAGE: [1,1,1,1], CRC_POLYNOMIAL: 0x1021, CRC_INIT: 0xFFFF, SAMPLE_RATE: 20, BIT_DURATION_DEFAULT: 1 };
global.GESTURE_DATA = require(path.join(root, 'receiver', 'standalone', 'js', 'gestures_embedded.js'));
require(path.join(root, 'receiver', 'standalone', 'js', 'crc16.js'));
const decoder = require(path.join(root, 'receiver', 'standalone', 'js', 'decoder.js'));
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const request = JSON.parse(input || '{}');
    let output;
    if (request.operation === 'functions') {
      const d = decoder;
      output = {
        movingAverage: d.movingAverage(request.data, request.window),
        lowPass: d.lowPass(request.data, request.cutoff, request.rate),
        baselineCorrection: d.baselineCorrection(request.data, request.baseline),
        otsu: d.computeOtsu(request.data),
        idle: d.computeFromIdle(request.data, request.idleStart, request.idleEnd, request.rate),
        adaptive: d.computeAdaptive(request.data, request.window),
        percentile: d.computePercentile(request.data, request.percentile),
        samplesToBits: d.samplesToBits(request.samples, request.threshold, request.bitDuration, request.rate),
        sync: d.findSyncHeader(request.bits),
        crc: global.CRC16.crc16ccitt(request.bits)
      };
    } else output = decoder.decodeRecordingMode(request.recording, request.mode, request.options || {});
    process.stdout.write(JSON.stringify(output));
  } catch (error) {
    process.stderr.write(String(error.stack || error));
    process.exitCode = 2;
  }
});
