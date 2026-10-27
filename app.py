import streamlit as st
import sqlite3, os, smtplib
from email.message import EmailMessage
from datetime import datetime,date,time,timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
DB=Path(__file__).parent/"dose_reminde.db"
st.set_page_config(page_title="Dose Reminder",page_icon="💊",layout="wide")
def con():
 c=sqlite3.connect(DB,timeout=15,check_same_thread=False);c.row_factory=sqlite3.Row;return c
with con() as c:
 c.execute("CREATE TABLE IF NOT EXISTS meds(id INTEGER PRIMARY KEY,name TEXT NOT NULL,label TEXT,instructions TEXT,times TEXT,days TEXT,start TEXT,end TEXT,active INTEGER DEFAULT 1,caregiver TEXT DEFAULT '',grace INTEGER DEFAULT 60)")
 c.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,mid INTEGER,day TEXT,clock TEXT,status TEXT,updated TEXT,UNIQUE(mid,day,clock))")
 c.execute("CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,mid INTEGER,day TEXT,clock TEXT,type TEXT,sent TEXT,UNIQUE(mid,day,clock,type))")
 cols={r["name"] for r in c.execute("PRAGMA table_info(meds)")}
 for nm,typ in [("caregiver","TEXT DEFAULT ''"),("grace","INTEGER DEFAULT 60")]:
  if nm not in cols:c.execute(f"ALTER TABLE meds ADD COLUMN {nm} {typ}")
if "lang" not in st.session_state:st.session_state.lang="English"
lang=st.sidebar.selectbox("Language / भाषा",["English","हिंदी"],index=0 if st.session_state.lang=="English" else 1);st.session_state.lang=lang
HI=lang=="हिंदी"
def T(a,b):return b if HI else a
st.markdown("<style>.block-container{max-width:1150px;padding-top:1.2rem}div.stButton>button{min-height:48px;font-size:17px;border-radius:12px}html,body{font-size:18px}</style>",unsafe_allow_html=True)
def allmed(active=False):
 with con() as c:return c.execute("SELECT * FROM meds"+(" WHERE active=1" if active else "")+" ORDER BY name").fetchall()
def status(mid,d,t):
 with con() as c:r=c.execute("SELECT status FROM logs WHERE mid=? AND day=? AND clock=?",(mid,d.isoformat(),t)).fetchone()
 return r["status"] if r else "Unconfirmed"
def setstatus(mid,d,t,s):
 with con() as c:c.execute("INSERT INTO logs(mid,day,clock,status,updated) VALUES(?,?,?,?,?) ON CONFLICT(mid,day,clock) DO UPDATE SET status=excluded.status,updated=excluded.updated",(mid,d.isoformat(),t,s,datetime.now().isoformat()))
def schedules(d):
 out=[]
 for m in allmed(True):
  if d<date.fromisoformat(m["start"]) or (m["end"] and d>date.fromisoformat(m["end"])) or d.strftime("%a") not in m["days"].split(","):continue
  for t in m["times"].split(","):out.append((t,m,status(m["id"],d,t)))
 return sorted(out,key=lambda x:x[0])
def mail(to,subject,body):
 msg=EmailMessage();msg["Subject"]=subject;msg["From"]=os.environ["DOSE_FROM_EMAIL"];msg["To"]=to;msg.set_content(body)
 with smtplib.SMTP(os.environ["DOSE_SMTP_HOST"],int(os.environ["DOSE_SMTP_PORT"]),timeout=15) as s:
  s.starttls();s.login(os.environ["DOSE_SMTP_USER"],os.environ["DOSE_SMTP_PASSWORD"]);s.send_message(msg)
def alerts_tick():
 now=datetime.now();d=now.date()
 with con() as c:
  for m in c.execute("SELECT * FROM meds WHERE active=1 AND caregiver<>''").fetchall():
   if d<date.fromisoformat(m["start"]) or (m["end"] and d>date.fromisoformat(m["end"])) or d.strftime("%a") not in m["days"].split(","):continue
   for t in m["times"].split(","):
    if now<datetime.combine(d,datetime.strptime(t,"%H:%M").time())+timedelta(minutes=int(m["grace"])):continue
    log=c.execute("SELECT status FROM logs WHERE mid=? AND day=? AND clock=?",(m["id"],d.isoformat(),t)).fetchone()
    if log and log["status"] in ("Taken","Skipped"):continue
    exists=c.execute("SELECT 1 FROM alerts WHERE mid=? AND day=? AND clock=? AND type='unconfirmed'",(m["id"],d.isoformat(),t)).fetchone()
    if exists:continue
    mail(m["caregiver"],"Dose Reminder: status unconfirmed",f"Scheduled dose remains unconfirmed. Medicine: {m['name']}; time: {t}; date: {d}. Please check directly with the older adult. This is not proof the dose was missed. Do not advise extra doses.")
    c.execute("INSERT OR IGNORE INTO alerts(mid,day,clock,type,sent) VALUES(?,?,?,?,?)",(m["id"],d.isoformat(),t,"unconfirmed",now.isoformat()))
def email_ready():return all(os.getenv(k) for k in ["DOSE_SMTP_HOST","DOSE_SMTP_PORT","DOSE_SMTP_USER","DOSE_SMTP_PASSWORD","DOSE_FROM_EMAIL"])
if "scheduler_on" not in st.session_state:
 st.session_state.scheduler_on=False
 if os.getenv("DOSE_ENABLE_EMAIL_ALERTS")=="1" and email_ready():
  try:
   scheduler=BackgroundScheduler(daemon=True);scheduler.add_job(alerts_tick,IntervalTrigger(minutes=1),id="dose-alerts",replace_existing=True,max_instances=1);scheduler.start();st.session_state.scheduler_on=True
  except Exception:pass
st.title("💚 Dose Reminder")
st.caption(T("A clear dose reminder and tracking website for older adults.","बुज़ुर्गों के लिए सरल डोज़ रिमाइंडर और ट्रैकिंग वेबसाइट।"))
st.warning(T("Follow the prescription. This tool does not prescribe, calculate, or change doses.","प्रिस्क्रिप्शन का पालन करें। यह टूल खुराक तय, गणना या बदलता नहीं है।"))
pages=[("Today","आज की डोज़"),("Add schedule","शेड्यूल जोड़ें"),("History","इतिहास"),("Manage","शेड्यूल प्रबंधन"),("Caregiver setup","केयरगिवर सेटअप"),("Help & safety","मदद और सुरक्षा")]
p=st.sidebar.radio(T("Menu","मेन्यू"),[T(a,b) for a,b in pages]);p=next(a for a,b in pages if T(a,b)==p);today=date.today()
if p=="Today":
 st.header(T("Today's doses","आज की डोज़"));st.write(today.strftime("%d %b %Y"));items=schedules(today)
 if not items:st.success(T("No scheduled doses today.","आज कोई डोज़ निर्धारित नहीं है।"))
 else:
  cols=st.columns(3)
  for col,s in zip(cols,["Taken","Skipped","Unconfirmed"]):col.metric(T(s,{"Taken":"ली गई","Skipped":"छोड़ी गई","Unconfirmed":"पुष्टि बाकी"}[s]),sum(x[2]==s for x in items))
  for t,m,s in items:
   with st.container(border=True):
    a,b=st.columns([3,2])
    with a:
     st.subheader("💊 "+m["name"]);st.markdown("### "+datetime.strptime(t,"%H:%M").strftime("%I:%M %p"))
     if m["label"]:st.write(T("Prescription label: ","प्रिस्क्रिप्शन: ")+m["label"])
     if m["instructions"]:st.write(m["instructions"])
     st.write(T("Status: ","स्थिति: ")+s)
     if s=="Unconfirmed" and datetime.now()>datetime.combine(today,datetime.strptime(t,"%H:%M").time())+timedelta(minutes=30):st.caption(T("Past scheduled time; status remains unconfirmed.","निर्धारित समय बीत गया; पुष्टि बाकी है।"))
    with b:
     if s!="Taken" and st.button(T("✓ Confirm Taken","✓ ली गई दर्ज करें"),key=f"take{m['id']}{t}",use_container_width=True):setstatus(m["id"],today,t,"Taken");st.rerun()
     if s=="Unconfirmed" and st.button(T("Skipped","छोड़ी गई"),key=f"skip{m['id']}{t}",use_container_width=True):setstatus(m["id"],today,t,"Skipped");st.rerun()
     if s!="Unconfirmed" and st.button(T("Undo status","स्थिति वापस करें"),key=f"undo{m['id']}{t}",use_container_width=True):setstatus(m["id"],today,t,"Unconfirmed");st.rerun()
 st.caption(T("Refresh to update. Reminders aren't guaranteed if the website/server is closed or offline.","अपडेट के लिए रीफ़्रेश करें। साइट/सर्वर बंद या ऑफलाइन होने पर रिमाइंडर की गारंटी नहीं।"))
elif p=="Add schedule":
 st.header(T("Add dose schedule","डोज़ शेड्यूल जोड़ें"));st.info(T("Enter a schedule verified from the current prescription.","मौजूदा प्रिस्क्रिप्शन से सत्यापित शेड्यूल ही दर्ज करें।"))
 weekdays=[("Mon","Monday","सोमवार"),("Tue","Tuesday","मंगलवार"),("Wed","Wednesday","बुधवार"),("Thu","Thursday","गुरुवार"),("Fri","Friday","शुक्रवार"),("Sat","Saturday","शनिवार"),("Sun","Sunday","रविवार")]
 with st.form("add",clear_on_submit=True):
  name=st.text_input(T("Medicine name *","दवा का नाम *"));label=st.text_input(T("Prescription label (optional)","प्रिस्क्रिप्शन लेबल (वैकल्पिक)"));instructions=st.text_area(T("Instructions (optional)","निर्देश (वैकल्पिक)"))
  times=[st.time_input(T("Time 1","समय 1"),time(9,0)).strftime("%H:%M")];second=st.checkbox(T("Add second time","दूसरा समय जोड़ें"))
  if second:times.append(st.time_input(T("Time 2","समय 2"),time(20,0)).strftime("%H:%M"))
  labels=[T(en,hi) for _,en,hi in weekdays];chosen=st.multiselect(T("Repeat on","दोहराएँ"),labels,default=labels)
  start=st.date_input(T("Start date","शुरू तारीख"),today);forever=st.checkbox(T("No end date","अंतिम तारीख नहीं"),True);end=None if forever else st.date_input(T("End date","अंतिम तारीख"),today)
  caregiver=st.text_input(T("Caregiver email (optional)","केयरगिवर ईमेल (वैकल्पिक)"));grace=st.selectbox(T("Alert after still unconfirmed (minutes)","पुष्टि बाकी होने पर अलर्ट (मिनट)"),[30,60,90,120],index=1)
  verified=st.checkbox(T("I checked this schedule against the prescription.","मैंने प्रिस्क्रिप्शन से शेड्यूल जाँचा है।"));save=st.form_submit_button(T("Save schedule","शेड्यूल सेव करें"),use_container_width=True)
  if save:
   days=[code for (code,en,hi),lab in zip(weekdays,labels) if lab in chosen]
   if not name.strip():st.error(T("Medicine name is required.","दवा का नाम ज़रूरी है।"))
   elif not days:st.error(T("Select at least one day.","कम से कम एक दिन चुनें।"))
   elif end and end<start:st.error(T("End date is invalid.","अंतिम तारीख सही नहीं है।"))
   elif caregiver and ("@" not in caregiver or "." not in caregiver):st.error(T("Check caregiver email.","केयरगिवर ईमेल जाँचें।"))
   elif not verified:st.error(T("Please verify the schedule first.","पहले शेड्यूल जाँचें।"))
   else:
    with con() as c:c.execute("INSERT INTO meds(name,label,instructions,times,days,start,end,caregiver,grace) VALUES(?,?,?,?,?,?,?,?,?)",(name.strip(),label.strip(),instructions.strip(),",".join(sorted(set(times))),",".join(days),start.isoformat(),end.isoformat() if end else "",caregiver.strip(),grace))
    st.success(T("Schedule saved.","शेड्यूल सेव हो गया।"));st.rerun()
elif p=="Manage":
 st.header(T("Manage schedules","शेड्यूल प्रबंधन"))
 for m in allmed():
  with st.container(border=True):
   st.subheader(m["name"]);st.write(" • ".join(m["times"].split(","))+" | "+m["days"]+" | "+("Active" if m["active"] else "Paused"));a,b=st.columns(2)
   with a:
    if st.button(T("Pause" if m["active"] else "Resume","रोकें" if m["active"] else "फिर शुरू करें"),key=f"pause{m['id']}"):
     with con() as c:c.execute("UPDATE meds SET active=? WHERE id=?",(0 if m["active"] else 1,m["id"]))
     st.rerun()
   with b:
    with st.popover(T("Remove schedule","शेड्यूल हटाएँ")):
     st.warning(T("This also removes tracking history.","इससे इतिहास भी हटेगा।"))
     if st.button(T("Confirm remove","हटाने की पुष्टि"),key=f"remove{m['id']}"):
      with con() as c:c.execute("DELETE FROM logs WHERE mid=?",(m["id"],));c.execute("DELETE FROM alerts WHERE mid=?",(m["id"],));c.execute("DELETE FROM meds WHERE id=?",(m["id"],))
      st.rerun()
elif p=="History":
 st.header(T("Dose history","डोज़ इतिहास"));d=st.date_input(T("Choose date","तारीख चुनें"),today);records=schedules(d)
 if records:
  for t,m,s in records:st.write(f"**{m['name']}** · {t} · {s}")
 else:st.info(T("No scheduled doses for this date.","इस तारीख पर कोई डोज़ शेड्यूल नहीं।"))
elif p=="Caregiver setup":
 st.header(T("Caregiver email alerts","केयरगिवर ईमेल अलर्ट"))
 st.success(T("Scheduler active in this app process.","इस ऐप प्रक्रिया में शेड्यूलर सक्रिय है।")) if st.session_state.scheduler_on else st.warning(T("Not active. SMTP settings and DOSE_ENABLE_EMAIL_ALERTS=1 are needed.","अभी सक्रिय नहीं। SMTP सेटिंग और DOSE_ENABLE_EMAIL_ALERTS=1 चाहिए।"))
 st.write(T("Get older adult's permission before adding a caregiver email. Alert means status unconfirmed, not proof of a missed dose.","केयरगिवर ईमेल जोड़ने से पहले बुज़ुर्ग की अनुमति लें। अलर्ट पुष्टि बाकी बताता है, छूटी डोज़ का प्रमाण नहीं।"))
 st.code('$env:DOSE_SMTP_HOST="smtp.example.com"\\n$env:DOSE_SMTP_PORT="587"\\n$env:DOSE_SMTP_USER="your-user"\\n$env:DOSE_SMTP_PASSWORD="your-app-password"\\n$env:DOSE_FROM_EMAIL="sender@example.com"\\n$env:DOSE_ENABLE_EMAIL_ALERTS="1"\\npython -m streamlit run app.py',language="powershell")
 st.caption(T("Use provider SMTP values. Keep secrets private; test delivery first.","ईमेल प्रदाता की SMTP जानकारी भरें। सीक्रेट सुरक्षित रखें; पहले टेस्ट करें।"))
else:
 st.header(T("Help & safety","मदद और सुरक्षा"))
 st.markdown(T("- Reminder/logging support only, not medical advice.\\n- Follow the current prescription.\\n- Status is user-reported, not proof of taking medicine.\\n- For late/uncertain doses, ask a pharmacist/clinician; never double a dose based on this website.\\n- Caregiver access requires consent.\\n- No authentication, secure roles, encrypted cloud database, backups, or production monitoring. Do not expose publicly or use real patient data.\\n- Scheduler runs only while this one app process is alive.",
 "- यह केवल रिमाइंडर/रिकॉर्ड सहायता है, मेडिकल सलाह नहीं।\\n- मौजूदा प्रिस्क्रिप्शन का पालन करें।\\n- स्टेटस दवा लेने का प्रमाण नहीं है।\\n- देर/संदेह पर डॉक्टर/फार्मासिस्ट से पूछें; ऐप के आधार पर दोहरी खुराक न लें।\\n- केयरगिवर एक्सेस के लिए सहमति ज़रूरी है।\\n- सुरक्षित लॉगिन, cloud सुरक्षा, बैकअप और production monitoring नहीं हैं। सार्वजनिक रूप से न खोलें/असली मरीज डेटा न डालें।\\n- शेड्यूलर केवल ऐप प्रक्रिया चलने तक चलता है।"))
