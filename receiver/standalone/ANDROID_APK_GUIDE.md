# Android APK wrapper with Capacitor
The wrapper runs the same single-file receiver locally. Runtime has no need for PC, network or internet. **Honest build limitation:** the commands below can be performed fully offline only if Node/npm, the required npm packages, Android Studio, Android SDK platforms/build-tools and Gradle dependencies are already installed/cached. A first-time Capacitor/Android setup commonly downloads packages/components and is not guaranteed offline.

## Project setup (run where build tools are installed)

```sh
mkdir offline-receiver-apk
cd offline-receiver-apk
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init
npx cap add android
mkdir www
```

For `npx cap init`, choose an app name (for example `Offline Receiver`) and app id (for example `org.example.offlinereceiver`). Copy the generated file `receiver/standalone/standalone_receiver.html` to `www/index.html` (PowerShell: `Copy-Item <path-to-project>\receiver\standalone\standalone_receiver.html www\index.html`). Ensure `capacitor.config.json` has `"webDir": "www"`. Then:

```sh
npx cap sync android
npx cap open android
```

In Android Studio, build the debug APK using **Build > Build Bundle(s) / APK(s) > Build APK(s)**. Transfer the resulting APK by USB and install it, allowing installation from that file source if Android asks. To rebuild after changing web content, replace `www/index.html`, run `npx cap sync android`, then rebuild.

## AndroidManifest.xml permissions
The core app does not need internet or Wi-Fi permissions. Add motion/sensor permissions only as required by the chosen native plugin. There is no universal runtime permission for the hardware magnetometer. Typical manifest entries for optional recording/export and plugin use are:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-feature android:name="android.hardware.sensor.compass" android:required="false" />
  <uses-feature android:name="android.hardware.sensor.accelerometer" android:required="false" />
  <application android:allowBackup="false" android:usesCleartextTraffic="false" ...>
    <!-- Do not add INTERNET unless your wrapper intentionally needs it. -->
  </application>
</manifest>
```

Do not add `INTERNET` or `ACCESS_WIFI_STATE` for this offline app. The manifest snippet is illustrative: merge the `<uses-feature>` elements into the project manifest and retain the generated application attributes. Android runtime sensor access is governed by the OS and WebView implementation; it is not enabled just by declaring a permission.

## Sensor support and native bridge
Capacitor's Android WebView may not expose the browser Generic Sensor `Magnetometer` API. The page attempts the Generic Sensor API first, then `devicemotion`, and labels that result as acceleration rather than magnetometer. `devicemotion` is not a faithful magnetometer substitute and some WebViews may not dispatch it.

For reliable magnetic capture in a WebView, install and audit a maintained Capacitor sensor plugin that exposes Android `Sensor.TYPE_MAGNETIC_FIELD` readings (for example, a plugin that returns x/y/z and timestamps), then add a small bridge that dispatches readings to the page. No plugin is bundled here, and plugin APIs/permissions vary by version. The page remains a functional offline JSON decoder if no sensor API/bridge is available. Test the selected plugin on the target phone; do not infer support from APK compilation.

## Offline build preparation
Before going offline, install Node/npm and Android Studio, install the Android SDK platform/build tools, execute the npm commands above, and allow Gradle to resolve all dependencies once. Keep the complete project, npm cache and Gradle cache. With those caches present, a subsequent web asset sync and APK build may work offline; Gradle can still attempt downloads if a needed artifact is absent. Runtime APK behavior does not require any of those build tools or network access.
