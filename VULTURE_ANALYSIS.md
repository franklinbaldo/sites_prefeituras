# Vulture Dead Code Analysis

**Date:** 2026-01-22
**Tool:** vulture (via uvx)
**Scope:** `src/sites_prefeituras/`

## Summary

Vulture found **51 potential dead code issues**. After manual verification:
- ✅ **5 confirmed dead code** (should be removed)
- ⚠️ **2 partially used** (need refactoring)
- ❌ **44 false positives** (Pydantic models, CLI commands, context managers)

---

## ✅ Confirmed Dead Code (Action Required)

### 1. Unused Import: `pandas` in storage.py
```python
# Line 10: src/sites_prefeituras/storage.py
import pandas as pd  # ← NEVER USED
```
**Action:** Remove the import. Pandas is in dependencies but not used.

---

### 2. Unused Import: `audit_batch` in cli.py
```python
# Line 14: src/sites_prefeituras/cli.py
from .collector import audit_single_site, audit_batch, BatchProcessor
#                                         ^^^^^^^^^^^^ NEVER USED
```
**Action:** Remove `audit_batch` from the import. Only `BatchProcessor` is used.

---

### 3. Unused Variable: `skipped_count` in collector.py
```python
# Lines 201-203: src/sites_prefeituras/collector.py
audit_count = 0
error_count = 0
skipped_count = 0  # ← Initialized but never incremented or used
```
**Action:** Either implement skip tracking or remove the variable.

---

### 4. Unused Method: `get_failed_urls()` in storage.py
```python
# Line 214: src/sites_prefeituras/storage.py
async def get_failed_urls(self, hours: int = 24) -> set[str]:
    """Retorna URLs que falharam nas ultimas N horas."""
    # ... implementation ...
```
**Usage:** Not called anywhere in codebase or tests.
**Action:** Remove unless planned for future use. Consider adding to quarantine functionality.

---

### 5. Unused Method: `export_for_dashboard()` in storage.py
```python
# Line 254: src/sites_prefeituras/storage.py
async def export_for_dashboard(self, output_file: Path) -> dict:
    """Exporta dados otimizados para dashboard."""
    # ... implementation ...
```
**Usage:** Not called anywhere. Dashboard export uses different methods.
**Action:** Remove. Dashboard export is handled by CLI `export-dashboard` command using other methods.

---

## ⚠️ Partially Used (Refactor Recommended)

### 1. Functions `process_urls_in_chunks()` and `audit_batch()`
```python
# Lines 254 & 303: src/sites_prefeituras/collector.py
async def process_urls_in_chunks(...):  # ← Only used in audit_batch()
async def audit_batch(...):             # ← Never called externally
```
**Analysis:** These appear to be legacy functions replaced by `BatchProcessor` class.
**Action:** Verify if still needed. If tests pass without them, remove.

---

## ❌ False Positives (Keep As-Is)

### 1. CLI Commands (60% confidence)
Vulture flags Typer commands as unused because they're called via CLI dispatch, not direct Python calls:
```python
@app.command()
def batch(...):  # ← Flagged as unused, but IS used via CLI
@app.command()
def serve(...):  # ← Flagged as unused, but IS used via CLI
@app.command()
def cleanup(...):  # ← Flagged as unused, but IS used via CLI
@app.command()
def export_dashboard(...):  # ← Flagged as unused, but IS used via CLI
```
**Verdict:** FALSE POSITIVE - These are CLI entry points.

---

### 2. Context Manager Protocol Parameters
```python
# Line 44: src/sites_prefeituras/collector.py
async def __aexit__(self, exc_type, exc_val, exc_tb):
    #                      ^^^^^^^^  ^^^^^^^  ^^^^^^
    #                      Required by Python protocol, even if unused
```
**Verdict:** FALSE POSITIVE - Required by `__aexit__` protocol.

---

### 3. Pydantic Model Fields (60% confidence)
All fields in `models.py` flagged as unused are actually used:
- **For data validation** when parsing PSI API responses
- **For serialization/deserialization** (JSON ↔ Python objects)
- **For type checking** with mypy

```python
class LighthouseMetric(BaseModel):
    id: str              # ← Used during JSON parsing
    title: str           # ← Used during JSON parsing
    score: Optional[float]  # ← Used during JSON parsing
    # ... etc
```
**Verdict:** FALSE POSITIVE - Pydantic fields are implicitly used.

---

### 4. Methods Used Only in Tests
```python
# storage.py
async def get_temporal_evolution(...)  # ← Used in test_aggregated_metrics.py
async def get_urls_to_skip_quarantine(...)  # ← Used in test_quarantine.py
```
**Verdict:** FALSE POSITIVE - Used in tests (vulture only scanned `src/`).

---

## Recommended Actions

### Immediate Cleanup (15 minutes)
```bash
# 1. Remove unused pandas import
# src/sites_prefeituras/storage.py:10
- import pandas as pd

# 2. Remove unused audit_batch import
# src/sites_prefeituras/cli.py:14
- from .collector import audit_single_site, audit_batch, BatchProcessor
+ from .collector import audit_single_site, BatchProcessor

# 3. Remove skipped_count variable
# src/sites_prefeituras/collector.py:203
- skipped_count = 0
```

### Verification Needed (1 hour)
```bash
# Run full test suite without these functions:
# src/sites_prefeituras/collector.py
# - process_urls_in_chunks()  (line 254)
# - audit_batch()             (line 303)

# If tests pass, remove them. If not, add tests or document usage.
```

### Safe to Remove (if not planned for future)
```bash
# src/sites_prefeituras/storage.py
# - get_failed_urls()        (line 214)
# - export_for_dashboard()   (line 254)
```

---

## Vulture Configuration

To reduce false positives in future runs, create `vulture_whitelist.py`:

```python
# vulture_whitelist.py
# CLI commands (called via Typer dispatch)
_.batch
_.serve
_.cleanup
_.export_dashboard

# Context manager protocol
_.__aexit__.exc_type
_.__aexit__.exc_val
_.__aexit__.exc_tb

# Pydantic model fields (used implicitly)
_.id
_.title
_.score
_.displayValue
_.requestedUrl
# ... etc
```

Then run: `uvx vulture src/ vulture_whitelist.py`

---

## Impact Assessment

| Category | Count | Lines of Code | Estimated Savings |
|----------|-------|---------------|-------------------|
| Dead imports | 2 | 2 lines | Minimal (cleanup) |
| Dead variables | 1 | 1 line | Minimal (clarity) |
| Dead methods | 2 | ~80 lines | Moderate (maintenance) |
| Dead functions | 2 | ~100 lines | High (if unused) |
| **Total** | **7** | **~183 lines** | **~8% of codebase** |

---

## Next Steps

1. ✅ Remove confirmed dead code (5 items)
2. ⚠️ Verify `process_urls_in_chunks()` and `audit_batch()` usage
3. 📝 Create `vulture_whitelist.py` for future scans
4. 🔄 Add vulture to CI pipeline (with whitelist)
5. 📊 Re-run after cleanup to verify

---

## False Positive Rate

- **Total findings:** 51
- **Real dead code:** 5-7 (10-14%)
- **False positives:** 44-46 (86-90%)

**Conclusion:** Vulture is useful but requires manual verification. Pydantic models and CLI frameworks generate many false positives.
