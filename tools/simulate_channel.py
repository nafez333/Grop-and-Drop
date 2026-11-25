# Synthetic magnetic-channel recording generator.
from __future__ import annotations
import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Sequence
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shared.constants import END_OF_MESSAGE, SAMPLE_RATE, SYNC_HEADER
from shared.protocol import Protocol
from gestures import GestureEngine
LOGGER=logging.getLogger(__name__)

def simulate_channel(bits: Sequence[int], output: Path, *, bit_duration: float=1.0,
                     sample_rate: float=SAMPLE_RATE, delta_ut: float=8.0,
                     snr_db: float=30.0, drift: float=0.0, jitter: float=0.002,
                     seed: int=77) -> Path:
    try:
        if bit_duration<=0 or sample_rate<=0 or delta_ut<=0: raise ValueError("duration, sample rate and delta must be positive")
        rng=random.Random(seed);sigma=delta_ut/(10**(snr_db/20));steps=max(1,round(sample_rate*bit_duration));samples=[];index=0
        # Include one explicit idle bit so threshold tests/calibration have a quiet segment.
        framed=[0]+list(bits)
        for bit in framed:
            for _ in range(steps):
                t=index/sample_rate+rng.uniform(-jitter,jitter)
                baseline=48.0+drift*index+0.25*math.sin(index/95)
                value=baseline+(delta_ut if bit else 0.0)+rng.gauss(0,sigma)
                samples.append({"t":round(t,7),"x":value,"y":baseline,"z":baseline})
                index+=1
        record={"metadata":{"timestamp":"2026-01-01T00:00:00Z","sample_rate_hz":sample_rate,"bit_duration_seconds":bit_duration,"sensor_type":"magnetometer","idle_start_index":0,"idle_end_index":steps,"channel":{"delta_uT":delta_ut,"snr_db":snr_db,"noise_sigma_uT":sigma,"drift_uT_per_sample":drift,"jitter_seconds":jitter}},"samples":samples}
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8");return output
    except (OSError,ValueError,TypeError) as error: raise RuntimeError(f"Channel simulation failed: {error}") from error

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True);group.add_argument("--message");group.add_argument("--gesture");parser.add_argument("--output",type=Path,default=ROOT/"tests"/"fixtures"/"simulated.json");parser.add_argument("--bit-duration",type=float,default=1.0);parser.add_argument("--sample-rate",type=float,default=SAMPLE_RATE);parser.add_argument("--delta",type=float,default=8.0);parser.add_argument("--snr",type=float,default=30.0);parser.add_argument("--seed",type=int,default=77);args=parser.parse_args(argv)
    if args.message is not None: bits=Protocol().encode_message(args.message)
    else:
        gesture_bits=GestureEngine(config_path=str(ROOT/"gestures"/"gestures.json")).get_bits(args.gesture);protocol=Protocol();crc=protocol.calculate_crc(gesture_bits);bits=list(SYNC_HEADER)+gesture_bits+[(crc>>shift)&1 for shift in range(15,-1,-1)]+list(END_OF_MESSAGE)
    path=simulate_channel(bits,args.output,bit_duration=args.bit_duration,sample_rate=args.sample_rate,delta_ut=args.delta,snr_db=args.snr,seed=args.seed);LOGGER.info("Wrote synthetic channel recording: %s",path);return 0
if __name__=="__main__":logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s");raise SystemExit(main())
