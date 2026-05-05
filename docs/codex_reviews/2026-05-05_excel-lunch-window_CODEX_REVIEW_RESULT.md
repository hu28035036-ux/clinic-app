**Findings**
- Medium: [app/routers/api.py](</c/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리/app/routers/api.py:4660>) only writes the lunch label when `ci == 0`. If the first therapist column has an appointment in the first lunch row, the `entry` branch wins and the `elif is_lunch` label branch is skipped, so no `"점심시간 HH:MM~HH:MM"` label is written anywhere. The requirement says appointment cells should keep priority, but the label should appear once in the first available empty lunch cell. Fix by tracking whether the label has been written and placing it in the first lunch empty cell across lunch rows/columns.

- Low: [tests/test_export_lunch_window.py](</c/Users/user/Desktop/새 폴더/병원예약관리/병원예약관리/tests/test_export_lunch_window.py:60>) does not cover the occupied-first-column case above. The current 3 tests prove disabled/no-label, enabled/label, and time-column grey, but they would pass even if real schedules lose the label whenever the first therapist is booked at lunch.

**Checklist Result**
- `lunch_slots` overlap condition: looks correct.
- `lunch_enabled=False`: covered.
- invalid `lunch_start/end`: implementation is graceful, but not tested.
- lunch slot with appointment: existing appointment cell is preserved.
- merged 60-minute appointment: existing skip handling is preserved.
- tests: useful baseline, but missing the occupied first lunch cell and invalid config cases.
- docs: review doc exists; I did not see a lunch-window-specific `CLAUDE.md` update in the inspected output.

I did not rerun pytest/ruff because this session is read-only and the new tests mutate `cfg.json`.