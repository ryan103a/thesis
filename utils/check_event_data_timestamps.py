#!/usr/bin/env python3
import sys
import h5py
import numpy as np

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} file.h5", file=sys.stderr)
    sys.exit(1)

path = sys.argv[1]
CHUNK = 10_000_000

n_bad = 0
worst = 0          # most negative step seen
worst_idx = None
prev_last = None

with h5py.File(path, "r") as f:
    t = f["t"]
    n = t.shape[0]
    print(f"{path}: {n} events, dtype {t.dtype}")

    for start in range(0, n, CHUNK):
        chunk = t[start:start + CHUNK].astype(np.int64)

        # include the step across the chunk boundary
        if prev_last is not None:
            chunk = np.concatenate(([prev_last], chunk))
            offset = start - 1
        else:
            offset = start

        d = np.diff(chunk)
        neg = np.flatnonzero(d < 0)
        n_bad += neg.size
        if neg.size:
            i = neg[np.argmin(d[neg])]
            if d[i] < worst:
                worst = int(d[i])
                worst_idx = offset + int(i) + 1

        prev_last = chunk[-1]

print(f"{n_bad} of {n - 1} steps go backwards")
if n_bad:
    print(f"worst backwards jump: {worst} (timestamp units, usually µs), at event index {worst_idx}")
