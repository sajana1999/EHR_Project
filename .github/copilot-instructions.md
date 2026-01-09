# Copilot / AI Agent Instructions — EHR_Project

Short, actionable guide to help an AI coding agent get productive with this repository.

## Quick summary
- Flask web app (single-process dev server) serving an EHR system from `app.py`.
- MySQL accessed via `pymysql`; DB name expected: `ehr_system`.
- Passwords stored with `flask_bcrypt` (see register/login flow in `app.py`).
- File uploads saved under `static/uploads` and referenced in DB as `uploads/<file>` (rendered via `url_for('static', filename=...)`).
- Templates live in `templates/` and use Bootstrap 5 + Flatpickr (CDNs in `layout.html` and `add_patient.html`).

## How to run locally
- Start MySQL and ensure a database named `ehr_system` exists and is reachable with credentials in `app.py`.
- Run the dev server: `python app.py` (debug mode enabled).
- Run schema-altering helpers if needed: `python update_db.py` and `python update_patients_db.py` (these ALTER existing tables to add columns).

## Key files & responsibilities
- `app.py` — Core app: routing, DB access (`get_db_connection()`), file upload handling, auth/session logic.
  - Auth/session keys: `session['logged_in']`, `session['doctor_id']`, `session['username']`.
  - Patient creation: see `add_patient()` for file handling, multi-document uploads, and DB insert queries.
- `update_db.py`, `update_patients_db.py` — Small scripts that add columns to `doctors` and `patients`. Run manually when needed.
- `templates/*` — Jinja templates. Notable examples:
  - `add_patient.html` — form fields: `first_name`, `last_name`, `insurance_number`, `age`, `weight`, `gender`, `allergies`, `appt_date`, `history`, `patient_img` and repeated `medical_docs` / `doc_dates` fields.
  - `dashboard.html` — shows how `patient.patient_img` is used with `url_for('static', filename=...)`.
- `static/uploads/` — Storage for uploaded files; created at runtime if missing.

## Project-specific patterns & gotchas (concrete examples)
- Multi-file + per-file date pairing: the form sends multiple inputs with the same name (`medical_docs`, `doc_dates`) and the server handles them as:
  ```py
  docs = request.files.getlist('medical_docs')
  dates = request.form.getlist('doc_dates')
  for doc, d_date in zip(docs, dates):
      # save file + insert into patient_documents with document_date = d_date
  ```
- File paths saved to DB are stored as `uploads/<filename>` (not including `static/`). Use `url_for('static', filename=doc.file_path)` to build urls.
- Filenames are made unique using `uuid.uuid4().hex + "_" + secure_filename(...)` in `add_patient()`.
- Date formats: Flatpickr is configured to submit `Y-m-d` (ISO `YYYY-MM-DD`) for `appt_date` input.
- Auth flow: `register()` hashes passwords with `bcrypt.generate_password_hash()`; `login()` checks with `bcrypt.check_password_hash()`.

## DB & schema notes (discoverable from code)
- Minimal schema expectations:
  - `doctors` table: contains `id`, `username`, `password`, and related doctor metadata (some columns added by `update_db.py`).
  - `patients` table: stores `first_name`, `last_name`, `insurance_number`, `age`, `weight`, `gender`, `allergies`, `appt_date`, `medical_history`, `patient_img`, `doctor_id`, etc.
  - `patient_documents` table: stores `patient_id`, `file_path`, `document_date` (inserted from the multi-file flow).
- No schema creation scripts are present — DB setup is expected to be manual or external; scripts only ALTER tables.

## Security & operational notes (observable issues to be careful about)
- Secrets are hardcoded in `app.py` and update scripts (`app.secret_key`, DB password). Do not expose these values in public commits or patches.
- `delete_patient` is implemented as a GET route — deletes records without CSRF protection; be cautious when changing or testing this behavior.
- Uploaded files are not removed when a patient is deleted (no cleanup implemented).

## Common tasks & where to make changes
- Add a route: edit `app.py`, add template under `templates/`, link via nav in `layout.html` if necessary.
- Add DB column: update `update_patients_db.py` or `update_db.py` and include ALTER statement; then update code that reads/writes the column.
- Change file upload behavior: modify `UPLOAD_FOLDER` logic in `app.py` and update any places where `file_path` is stored or rendered.

---
If anything above is unclear or you'd like me to expand a section (DB schema examples, adding a unit test strategy, or a migration plan), tell me which area to expand and I will iterate. ✅
