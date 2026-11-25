# مستقبل مستقل — Offline Receiver
This is a self-contained HTML page and operates in airplane mode. It makes no network requests. Sensor availability is separate from decoding: JSON import and on-device decoding still work if the browser blocks sensors.

## 1. Copy to the phone / نقل الملف إلى الهاتف
1. Build once on the development machine: `python receiver/standalone/build_standalone.py`.
2. Connect the Android phone by USB, choose **File transfer**, and copy `receiver/standalone/standalone_receiver.html` to `Internal storage/Download/receiver/standalone_receiver.html`.
3. For Path A, also copy the same file into a directory accessible to Termux at `/sdcard/Download/receiver/`.
4. Disconnect the cable. All runtime operation is local and offline.

## Path A — Phone-local server (recommended for sensors)

Install Termux from a trusted distribution, grant storage access once (`termux-setup-storage`), then run these exact commands:

```sh
pkg install python
cd /sdcard/Download/receiver
python -m http.server 8080 --bind 127.0.0.1
```

Keep Termux running and open this address in Chrome on the same phone:

`http://127.0.0.1:8080/standalone_receiver.html`

The page checks `window.isSecureContext` and displays a red/green state. Browsers treat loopback as a potentially trustworthy origin, but sensor API support and user permission are still browser/device dependent. If Chrome shows an insecure state, confirm the address uses `127.0.0.1` (not the phone's LAN address) and grant the requested motion/sensor permission.

A local HTTP server app can be used instead of Termux if it can bind specifically to `127.0.0.1` and serve the Download folder. Disable network access if desired; the loopback server itself does not require Wi-Fi or internet.

## Path B — Offline APK wrapper
Follow [`ANDROID_APK_GUIDE.md`](ANDROID_APK_GUIDE.md). A previously built APK runs without network permission. Installing/building the Android project may require Android Studio, Gradle, SDK components and npm package downloads unless these tools and dependencies have already been cached. No claim of a first-time, zero-internet APK build is made.

## Path C — `file://` degraded decoder
Open the HTML from Files/Downloads. The sensor banner will warn that sensors may be blocked. Tap **Import JSON**, select a recording exported by this app or the online receiver, and the decoder, chart, result panel, saved list and JSON export work on the phone without network. Sensor capture is not promised on `file://`.

## Controls
- **Start / Stop** captures supported sensor data. Device-motion fallback is explicitly identified as acceleration, not magnetometer.
- **Decode** runs the Python-compatible decoding pipeline locally; **Export JSON** downloads the current samples.
- Choose bit duration and threshold mode. Idle threshold requires **Calibrate idle** (hold still for three seconds). On the current pipeline, imported recordings are decoded using the canonical Python receiver path by default; non-Otsu options apply the UI's selected threshold to extracted values.
- Saved recordings persist in IndexedDB. If IndexedDB is unavailable, localStorage fallback is guarded at 3 MB. Export and delete older recordings if full.
- **Run parity self-test** compares the embedded expected Python output for `data/recordings/example_recording.json` to the live JavaScript decoder.

## Troubleshooting / استكشاف الأخطاء
| Problem | Action |
|---|---|
| Sensor blocked / no sensor API | Use Path A on Android Chrome, grant the permission prompt, confirm hardware support. Or import JSON (Path C). |
| Not a secure context | Open `http://127.0.0.1:8080/standalone_receiver.html` from a server running on the phone, or use the APK. Do not use a LAN IP. |
| iOS limitations | iOS Safari commonly requires a user gesture for motion permission and may not expose Generic Sensor magnetometer. Use JSON import or a verified native wrapper; sensor support is not guaranteed. |
| Quota exceeded | Export important recordings and delete old entries. IndexedDB is primary; localStorage fallback limit is 3 MB. |
| Empty decode / no sync | Verify correct recording, sample rate, bit duration and threshold. The sample fixture is synthetic and intentionally need not contain a valid frame. |
| Termux URL unavailable | Keep `http.server` running, confirm port 8080, and use the exact loopback URL on the same phone. |

## Rebuild and verify
From the project root: `python tools/export_gestures_to_js.py`, then `python receiver/standalone/build_standalone.py`. The build reads gesture data and protocol constants from canonical project sources, embeds the Python parity fixture, scans for external resource URLs and rejects output at/above 500 KB. Run parity checks with `python -m unittest tests.test_crc16_parity tests.test_decoder_parity`.
