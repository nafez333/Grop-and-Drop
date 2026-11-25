"""AirGesture - natural hand gesture control for Windows desktops.

The package is split into three clear layers:

``airgesture.core``
    Pure, side-effect free logic (geometry, pose analysis, gesture
    recognition, settings). No OpenCV, no MediaPipe, no UI. Fully unit
    testable without a camera.

``airgesture.runtime``
    Stateful services that talk to hardware / the operating system:
    camera, MediaPipe tracking, mouse control and the interaction state
    machine that ties everything together.

``airgesture.ui``
    Tkinter views. The UI only renders state pushed by the engine bridge
    and forwards user commands; it never blocks on vision processing.
"""

__version__ = "2.0.0"
APP_NAME = "AirGesture"
