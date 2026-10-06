"""Run every extension script in order: python analysis/extensions/run_all.py"""
import runpy, sys, time
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
for s in ["01_h3_moderation.py", "02_exposure_capacity.py", "03_dynamics_2013_2025.py",
          "04_education_controls.py", "05_map.py", "06_h3_zensus2011.py"]:
    t = time.time(); print(f"\n=== {s}")
    try:
        runpy.run_path(str(here / s), run_name="__main__")
    except SystemExit as e:
        print(e)
    print(f"    done in {time.time() - t:.0f}s")
