# Dose Reminder — enhanced Streamlit starter
## Windows setup
Open folder in VS Code terminal:
```powershell
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Open Streamlit's local URL, usually http://localhost:8501.

## Features
- Hindi/English UI, accessible large controls
- Add prescription-verified schedules, weekdays, date range and up to two times
- SQLite persistence
- Taken/Skipped/Unconfirmed tracking
- Pause/resume/remove, date history
- Optional caregiver email alert after configured grace window

## Optional email alerts
Set environment variables in the same PowerShell terminal; use provider SMTP details and an app-specific password. Keep credentials private:
```powershell
$env:DOSE_SMTP_HOST="smtp.example.com"
$env:DOSE_SMTP_PORT="587"
$env:DOSE_SMTP_USER="your-user"
$env:DOSE_SMTP_PASSWORD="your-app-password"
$env:DOSE_FROM_EMAIL="sender@example.com"
$env:DOSE_ENABLE_EMAIL_ALERTS="1"
python -m streamlit run app.py
```
Test delivery first. An alert means unconfirmed, not proof a dose was missed.

## Important limitations
Learning/demo prototype only. No user authentication, caregiver verification or fine-grained access, encrypted cloud database, secure backups, audit controls, production scheduler or monitoring. Do not expose publicly or enter actual patient information.
Email scheduler runs inside this Streamlit process; it stops if host sleeps/stops and is unsuitable for multi-worker production hosting. Use a separate reliable scheduler worker, access controls, consent, timezone handling, retries and delivery monitoring before real-world deployment.
A user-reported status is not proof of medicine intake. The app must not recommend, calculate or alter doses.
