"""Does PWFTS (pyFTS) run with current numpy and pandas, and how does it behave on a short,
capped occupancy-like series? Synthetic data only. See ../pwfts-assessment.md.

Setup (in a separate environment, not the project one):

    python -m venv .venv-pyfts
    .venv-pyfts/bin/pip install numpy pandas scipy matplotlib dill scikit-learn
    .venv-pyfts/bin/pip install git+https://github.com/PYFTS/pyFTS

Then patch the installed package (pyFTS has had no release since 2019):
1. In pyFTS/common/transformations/trend.py replace `from pandas import datetime`
   with `from datetime import datetime` (removed in pandas 2.0).
2. In pyFTS/common/Transformations.py wrap the SOMTransformation and
   AutoencoderTransformation imports in try/except ImportError (they need Keras).

Run: .venv-pyfts/bin/python pwfts_check.py
"""

import warnings

import numpy as np
from pyFTS.models import pwfts
from pyFTS.partitioners import Grid

warnings.simplefilter("ignore")

rng = np.random.default_rng(0)
CAPACITY = 248  # Medium class
N = 100

# Synthetic occupancy: drift, weekday pattern and noise, capped at capacity
x = [200.0]
for t in range(1, N):
    weekday = t % 7
    flow = (6 if weekday < 5 else 9) - (7 if weekday < 5 else 1) + rng.normal(0, 4)
    x.append(min(CAPACITY, max(0, x[-1] + flow)))
x = np.array(x)
train, test = x[:86], x[86:]

part = Grid.GridPartitioner(data=train, npart=15)
model = pwfts.ProbabilisticWeightedFTS(partitioner=part, order=1)
model.fit(train)

point = model.predict(train[-1:], steps_ahead=14)
interval = model.predict(train[-1:], type="interval", steps_ahead=14)
dist = model.predict(train[-1:], type="distribution", steps_ahead=14)

print("rules learned:", len(model.flrgs))
print("point, first 3 days:", np.round(point[:3], 1))
print("interval, day 2:", np.round(interval[1], 1), "capacity:", CAPACITY)
print("distribution objects:", len(dist))
print("MAE (cells):", round(float(np.mean(np.abs(np.array(point[:14]) - test))), 1))
print("persistence MAE (cells):", round(float(np.mean(np.abs(train[-1] - test))), 1))
