import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tests.synthetic import open_palm, fist, index_only, pinch, two_fingers, three_fingers, four_fingers
from airgesture.core.pose import analyze
from airgesture.core.recognizer import GestureRecognizer

rec = GestureRecognizer(sensitivity=0.5)
for name, builder in [("open_palm", open_palm), ("fist", fist), ("index_only", index_only), ("pinch", pinch), ("two_fingers", two_fingers), ("three_fingers", three_fingers), ("four_fingers", four_fingers)]:
    pose = analyze(builder())
    det = rec.recognize(pose)
    print(name, "gesture=", det.gesture, "score=", round(det.score, 2),
          "index=", pose.finger_state("index"), "middle=", pose.finger_state("middle"),
          "ring=", pose.finger_state("ring"), "pinky=", pose.finger_state("pinky"), "thumb=", pose.finger_state("thumb"),
          "ext_index=", round(pose.extension["index"], 2), "ext_middle=", round(pose.extension["middle"], 2),
          "curl_middle=", round(pose.curl["middle"], 2), "curl_index=", round(pose.curl["index"], 2))