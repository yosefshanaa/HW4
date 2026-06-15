---
type: wiki
status: generated
project: werkzeug-analysis
---
# community 28 — 3 nodes cluster

## Summary
Community 28 is characterized by a three-node cluster that focuses on testing the functionality of the Watchdog Reloader Loop within the Werkzeug library. The tests, located in the `tests/test_serving.py` file, specifically assess the behavior of the reloader when handling closed and opened files. The evidence suggests a strong implementation relationship between the tests and the reloader's functionality.

## Evidence
- tests.test_serving.test_watchdog_reloader_ignores_closed_no_write —calls→ werkzeug._reloader.WatchdogReloaderLoop (EXTRACTED, 1.00) · tests/test_serving.py
- tests.test_serving.test_watchdog_reloader_ignores_closed_no_write —implements→ tests.test_serving (EXTRACTED, 1.00) · tests/test_serving.py
- tests.test_serving.test_watchdog_reloader_ignores_opened —calls→ werkzeug._reloader.WatchdogReloaderLoop (EXTRACTED, 1.00) · tests/test_serving.py
- tests.test_serving.test_watchdog_reloader_ignores_opened —implements→ tests.test_serving (EXTRACTED, 1.00) · tests/test_serving.py
- werkzeug._reloader.WatchdogReloaderLoop —implements→ werkzeug._reloader (EXTRACTED, 1.00) · src/werkzeug/_reloader.py
- werkzeug._reloader.WatchdogReloaderLoop.__enter__ —implements→ werkzeug._reloader.WatchdogReloaderLoop (EXTRACTED, 1.00) · src/werkzeug/_reloader.py

## Links
- [[index]]

## Open questions
- What specific scenarios are being tested in the `test_watchdog_reloader_ignores_closed_no_write` and `test_watchdog_reloader_ignores_opened` tests?
- How does the Watchdog Reloader Loop interact with other components of the Werkzeug library beyond the current tests?
- Are there additional edge cases or performance considerations that should be addressed in future tests of the Watchdog Reloader Loop?
