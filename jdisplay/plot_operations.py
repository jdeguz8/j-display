from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Tuple, Optional, List

import matplotlib.pyplot as plt

Row = Tuple[str, Optional[float], Optional[float], Optional[float]]
# rows from DBOperations.fetch_data(): (sample_date, min, max, avg)

class PlotOps:
    def __init__(self, out_dir: str | Path = "plots"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clean_avg(rows: Iterable[Row]) -> List[Tuple[str, float]]:
        """Return [(date, avg_float)].
        If avg is None but min/max exist, use midpoint (min+max)/2."""
        out: List[Tuple[str, float]] = []
        for d, mn, mx, av in rows:
            val = None
            if av is not None:
                try:
                    val = float(av)
                except (TypeError, ValueError):
                    val = None
            if val is None and mn is not None and mx is not None:
                try:
                    val = (float(mn) + float(mx)) / 2.0
                except (TypeError, ValueError):
                    val = None
            if val is not None:
                out.append((d, val))
        return out

    def boxplot_by_month(self, rows: Iterable[Row], *, show=True, save=False, fname="box_by_month.png"):
        means = self._clean_avg(rows)
        if not means:
            print("" \
            "==========================================================\n"
            "No usable values for this selection (avg/min/max missing).\n" \
            "=========================================================="
            )
            return

        by_m = defaultdict(list)
        for d, av in means:
            m = int(d[5:7])
            by_m[m].append(av)

        data = [by_m[m] for m in range(1, 13)]
        labels = [str(m) for m in range(1, 13)]

        plt.figure()
        plt.boxplot(data, labels=labels, showfliers=False)
        plt.title("Mean Temperature Distribution by Month")
        plt.xlabel("Month")
        plt.ylabel("Mean (°C)")
        plt.tight_layout()

        if save:
            p = self.out_dir / fname
            plt.savefig(p, dpi=144)
            print(f"Saved: {p.resolve()}")
        if show:
            plt.show()
        else:
            plt.close()

    def line_for_month(self, rows: Iterable[Row], year: int, month: int, *, show=True, save=False):
        means = self._clean_avg(rows)
        xs, ys = [], []
        for d, av in means:
            y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
            if y == year and m == month:
                xs.append(day)
                ys.append(av)

        # ensure chronological order
        if xs:
            pairs = sorted(zip(xs, ys))
            xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]

        if not xs:
            print("" \
            "============================================================================\n" \
            "No usable values for that month. Try seeding that month or a different one.\n" \
            "============================================================================")
            return

        plt.figure()
        plt.plot(xs, ys, marker="o")
        plt.title(f"Daily Mean Temp — {year}-{month:02d}")
        plt.xlabel("Day")
        plt.ylabel("Mean (°C)")
        plt.tight_layout()

        if save:
            p = self.out_dir / f"line_{year}-{month:02d}.png"
            plt.savefig(p, dpi=144)
            print(f"Saved: {p.resolve()}")
        if show:
            plt.show()
        else:
            plt.close()
