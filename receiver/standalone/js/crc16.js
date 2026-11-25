(function(root){'use strict';
function crc16ccitt(bits, poly, init){
  try {
    poly = poly === undefined ? (root.APP_PROTOCOL ? root.APP_PROTOCOL.CRC_POLYNOMIAL : 0x1021) : Number(poly);
    init = init === undefined ? (root.APP_PROTOCOL ? root.APP_PROTOCOL.CRC_INIT : 0xFFFF) : Number(init);
    if (!Number.isInteger(poly) || poly < 0 || poly > 0xFFFF || !Number.isInteger(init) || init < 0 || init > 0xFFFF) throw new RangeError('Polynomial and initial value must be 16-bit integers');
    let crc = init;
    for (const item of bits) { const bit = Number(item); if (bit !== 0 && bit !== 1) throw new TypeError('Bits must contain only 0 and 1'); const feedback = ((crc >>> 15) & 1) ^ bit; crc = (crc << 1) & 0xFFFF; if (feedback) crc ^= poly; }
    return crc;
  } catch (error) { throw new Error('CRC-16-CCITT failed: ' + error.message); }
}
const api = Object.freeze({crc16ccitt:crc16ccitt}); root.CRC16 = api;
if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
