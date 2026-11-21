"""Stage implementations for ``scripts/harness-smoke.py``.

Split out of the single script so every file stays under the repo's
400-line cap (``scripts/check-file-length.py``). ``scripts/`` is still not a
package: the driver puts ``scripts/`` on ``sys.path`` and imports this one.
"""
