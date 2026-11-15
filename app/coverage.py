"""Compact, frame-indexed camera homographies for the pitch viewer."""

from array import array
import csv
import math
from pathlib import Path


class CameraMapping:
    def __init__(self, path: str | Path):
        self.matrices = array('d')
        with Path(path).open(newline='') as handle:
            for expected, row in enumerate(csv.DictReader(handle)):
                if int(row['frame']) != expected:
                    raise ValueError('Homography frames must be contiguous and zero-based')
                values = [float(row[f'h{r}{c}']) for r in range(3) for c in range(3)]
                valid = int(row['valid']) == 1 and all(math.isfinite(v) for v in values)
                self.matrices.extend(values if valid else [math.nan] * 9)

    def window(self, start: int, stop: int) -> list[list[float] | None]:
        """Preserve every video frame, including missing mappings, without interpolation."""
        result = []
        for frame in range(start, stop):
            values = self.matrices[frame * 9:(frame + 1) * 9]
            result.append(list(values) if len(values) == 9 and math.isfinite(values[0]) else None)
        return result
