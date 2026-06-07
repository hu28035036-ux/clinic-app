"""Treatment constants and compatibility exports.

Treatment rows are managed in the database. Initial seed rows are loaded from
``app/data/default_treatments.json`` or the user-editable APPDATA copy.
"""

from app.modules.treatments.defaults import default_treatment_tuples


ROLE_DOCTOR = "doctor"
ROLE_THERAPIST = "therapist"
ROLES = [ROLE_DOCTOR, ROLE_THERAPIST]

# Backward compatibility for older imports. New seed code reads JSON directly.
SEED_TREATMENTS = default_treatment_tuples()

# Special shared ESWT code. The treatment row itself remains DB-managed.
ESWT_CODE = "eswt"
