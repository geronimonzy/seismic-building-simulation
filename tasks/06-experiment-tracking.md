# Task 06: Experiment Tracking

## Priority: MEDIUM
## Estimated Effort: 2-3 days

## Problem Statement

The current codebase:
- Has no way to track multiple analysis runs
- Cannot compare results across different configurations
- Has no searchable history of past analyses
- Makes reproducing previous results difficult

## Implementation Plan

### 1. Create tracking module
Create `src/seismic_twin/tracking/experiments.py`

### 2. Implement ExperimentTracker class

```python
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

class ExperimentTracker:
    """Log and retrieve analysis runs (like MLflow for structural dynamics)."""

    def __init__(self, db_path: str = ".seismic_experiments.db"):
        """
        Parameters:
        -----------
        db_path : str
            Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    building_n_stories INTEGER,
                    target_pga REAL,
                    method TEXT,
                    initial_nrmse REAL,
                    final_nrmse REAL,
                    config_json TEXT,
                    results_file TEXT,
                    tags TEXT,
                    notes TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    step INTEGER,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_project
                ON runs (project_name)
            """)

            conn.commit()
```

### 3. Implement logging methods

```python
def log_run(
    self,
    project_name: str,
    config: 'ProjectConfig',
    initial_nrmse: float,
    final_nrmse: float,
    results_file: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: str = "",
) -> int:
    """
    Log a completed analysis run.

    Returns:
        run_id: Unique identifier for this run
    """
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO runs
            (timestamp, project_name, building_n_stories, target_pga,
             method, initial_nrmse, final_nrmse, config_json,
             results_file, tags, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            project_name,
            config.building.n_stories,
            config.ground_motion.target_pga,
            config.calibration.optimization_method,
            initial_nrmse,
            final_nrmse,
            config.model_dump_json(),
            results_file,
            json.dumps(tags or []),
            notes,
        ))
        conn.commit()
        return cursor.lastrowid

def log_metric(
    self,
    run_id: int,
    metric_name: str,
    metric_value: float,
    step: Optional[int] = None,
) -> None:
    """Log a metric value for a run (e.g., iteration NRMSE)."""
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("""
            INSERT INTO metrics (run_id, metric_name, metric_value, step)
            VALUES (?, ?, ?, ?)
        """, (run_id, metric_name, metric_value, step))
        conn.commit()
```

### 4. Implement query methods

```python
def query_runs(
    self,
    project_name: Optional[str] = None,
    min_nrmse: Optional[float] = None,
    max_nrmse: Optional[float] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100,
) -> List[Dict]:
    """
    Query past runs with filters.

    Returns list of run dicts.
    """
    query = "SELECT * FROM runs WHERE 1=1"
    params = []

    if project_name:
        query += " AND project_name = ?"
        params.append(project_name)

    if min_nrmse is not None:
        query += " AND final_nrmse >= ?"
        params.append(min_nrmse)

    if max_nrmse is not None:
        query += " AND final_nrmse <= ?"
        params.append(max_nrmse)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def get_run(self, run_id: int) -> Optional[Dict]:
    """Get a specific run by ID."""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

def get_run_metrics(self, run_id: int) -> List[Dict]:
    """Get all metrics for a run."""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM metrics WHERE run_id = ? ORDER BY step",
            (run_id,)
        ).fetchall()
        return [dict(row) for row in rows]

def get_best_run(self, project_name: str) -> Optional[Dict]:
    """Get the run with lowest final NRMSE for a project."""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT * FROM runs
            WHERE project_name = ?
            ORDER BY final_nrmse ASC
            LIMIT 1
        """, (project_name,)).fetchone()
        return dict(row) if row else None
```

### 5. Add comparison utilities

```python
def compare_runs(self, run_ids: List[int]) -> Dict:
    """
    Compare multiple runs side-by-side.

    Returns dict with comparison table.
    """
    runs = [self.get_run(rid) for rid in run_ids]
    runs = [r for r in runs if r is not None]

    return {
        'runs': runs,
        'metrics': {
            'initial_nrmse': [r['initial_nrmse'] for r in runs],
            'final_nrmse': [r['final_nrmse'] for r in runs],
            'improvement': [
                (r['initial_nrmse'] - r['final_nrmse']) / r['initial_nrmse'] * 100
                for r in runs
            ],
        }
    }

def export_runs_csv(self, filename: str, project_name: Optional[str] = None) -> None:
    """Export runs to CSV file."""
    import csv
    runs = self.query_runs(project_name=project_name, limit=10000)

    if not runs:
        return

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=runs[0].keys())
        writer.writeheader()
        writer.writerows(runs)
```

### 6. Add context manager for automatic logging

```python
from contextlib import contextmanager

@contextmanager
def tracked_analysis(
    tracker: ExperimentTracker,
    project_name: str,
    config: 'ProjectConfig',
    notes: str = "",
):
    """
    Context manager for automatic run tracking.

    Usage:
        with tracked_analysis(tracker, "my_project", config) as run:
            # Do analysis
            run.log_metric("nrmse", 0.05, step=1)
            run.set_result(initial_nrmse=0.2, final_nrmse=0.05)
    """
    class RunContext:
        def __init__(self):
            self.run_id = None
            self.initial_nrmse = None
            self.final_nrmse = None

        def log_metric(self, name, value, step=None):
            if self.run_id:
                tracker.log_metric(self.run_id, name, value, step)

        def set_result(self, initial_nrmse, final_nrmse):
            self.initial_nrmse = initial_nrmse
            self.final_nrmse = final_nrmse

    ctx = RunContext()
    try:
        yield ctx
    finally:
        if ctx.initial_nrmse is not None:
            ctx.run_id = tracker.log_run(
                project_name, config,
                ctx.initial_nrmse, ctx.final_nrmse,
                notes=notes
            )
```

### 7. Add tests

- Test database creation
- Test run logging and retrieval
- Test metric logging
- Test query filters
- Test CSV export

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/tracking/__init__.py` | Create |
| `src/seismic_twin/tracking/experiments.py` | Create |
| `tests/test_experiments.py` | Create |

## Dependencies

None (uses standard library sqlite3)

## Success Criteria

- [ ] Can log analysis runs with all metadata
- [ ] Can query runs by project, NRMSE, tags
- [ ] Can track metrics over calibration iterations
- [ ] Can compare multiple runs
- [ ] Can export to CSV
- [ ] Context manager works for automatic tracking
- [ ] All tests pass

## Example Usage

```python
from seismic_twin.tracking import ExperimentTracker, tracked_analysis

tracker = ExperimentTracker("experiments.db")

# Manual logging
run_id = tracker.log_run(
    project_name="christchurch_v1",
    config=config,
    initial_nrmse=0.25,
    final_nrmse=0.04,
    tags=["production", "validated"],
    notes="Final calibration with updated sensors"
)

# Query best runs
best = tracker.get_best_run("christchurch_v1")
print(f"Best NRMSE: {best['final_nrmse']}")

# Automatic tracking
with tracked_analysis(tracker, "test_project", config) as run:
    for i in range(10):
        nrmse = calibrate_iteration(i)
        run.log_metric("nrmse", nrmse, step=i)
    run.set_result(initial_nrmse=0.3, final_nrmse=nrmse)
```
