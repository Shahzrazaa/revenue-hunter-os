from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json, re, uuid, os, smtplib, ssl
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')

BASE=Path(__file__).resolve().parents[1]
DB=BASE/'data'/'opportunities.json'
app=FastAPI(title='Revenue Hunter OS', version='0.4.0')
app.mount('/static', StaticFiles(directory=BASE/'static'), name='static')
templates=Jinja2Templates(directory=BASE/'templates')

def load():
    if not DB.exists(): return []
    try:
        return json.loads(DB.read_text())
    except (json.JSONDecodeError, OSError):
        return []

def save(rows):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(rows,indent=2))

def score(title, description, budget, source):
    text=(title+' '+description).lower(); s=35; reasons=[]
    ai=['ai','automation','creative','ugc','ads','research','python','agent','marketing','ecommerce','meta']
    hits=sum(1 for x in ai if x in text); s+=min(hits*6,30)
    if budget>=500: s+=15; reasons.append('budget ≥ $500')
    elif budget>=250: s+=8; reasons.append('paid-trial sized budget')
    if any(x in text for x in ['urgent','asap','immediately','this week','trial']): s+=10; reasons.append('fast sales signal')
    if any(x in text for x in ['worldwide','remote','global']): s+=5; reasons.append('international-friendly')
    if source.lower() in ['upwork','contra','linkedin','direct prospect']: s+=3; reasons.append('actionable source')
    if hits: reasons.append(f'{hits} AI/service-fit signals')
    return min(s,100), reasons

def generate_pitch(o):
    return (f"Hi — I looked at your {o['title']} requirement. Instead of starting with a long engagement, "
            f"I can deliver a focused 48-hour paid sprint: research the buyer/market, identify the strongest angles, "
            f"and produce execution-ready assets. For this brief I'd start with the highest-leverage bottleneck in your description, "
            f"then give you a compact test pack you can evaluate immediately. If it performs, we scale from there.\n\n"
            f"Suggested trial: ${max(250,min(500,o['budget'] or 350))} fixed. No long commitment.")

@app.get('/', response_class=HTMLResponse)
def home(request:Request):
    rows=sorted(load(), key=lambda x:x['score'], reverse=True)
    collected=sum(float(r.get('budget') or 0) for r in rows if r.get('status')=='Paid')
    source_stats={}
    for r in rows:
        src=r.get('source') or 'Unknown'
        st=source_stats.setdefault(src, {'targets':0,'pitched':0,'replied':0,'paid':0,'revenue':0.0})
        st['targets']+=1
        if r.get('status') in ['Pitched','Replied','Paid']: st['pitched']+=1
        if r.get('status') in ['Replied','Paid']: st['replied']+=1
        if r.get('status')=='Paid':
            st['paid']+=1; st['revenue']+=float(r.get('budget') or 0)
    hunters=[
      {'name':'Direct DTC','job':'Find brands + creative-service buyers','state':'ACTIVE'},
      {'name':'Freelance Intel','job':'Use marketplaces as demand intelligence','state':'ACTIVE'},
      {'name':'Kaggle','job':'Track prize/badge opportunities','state':'READY'},
      {'name':'Automation Gigs','job':'Find AI workflow / agent buyers','state':'ACTIVE'},
      {'name':'Bounties','job':'Track legitimate contests + paid challenges','state':'READY'},
    ]
    return templates.TemplateResponse('index.html', {'request':request,'rows':rows,'total':len(rows),'hot':sum(r['score']>=70 for r in rows),'collected':collected,'source_stats':source_stats,'hunters':hunters})

@app.post('/opportunities')
def add(title:str=Form(...), description:str=Form(...), budget:float=Form(0), source:str=Form('Manual'), url:str=Form('')):
    rows=load(); sc,reasons=score(title,description,budget,source)
    o={'id':str(uuid.uuid4())[:8],'title':title,'description':description,'budget':budget,'source':source,'url':url,'score':sc,'reasons':reasons,'status':'New','created':datetime.utcnow().isoformat(timespec='seconds')}
    o['pitch']=generate_pitch(o); rows.append(o); save(rows)
    return RedirectResponse('/',303)

@app.post('/opportunities/{oid}/status')
def status(oid:str, status:str=Form(...)):
    rows=load()
    for r in rows:
        if r['id']==oid:r['status']=status
    save(rows); return RedirectResponse('/',303)

@app.get('/api/opportunities')
def api(): return JSONResponse(sorted(load(),key=lambda x:x['score'],reverse=True))

@app.post('/opportunities/{oid}/delete')
def delete(oid:str):
    rows=[r for r in load() if r['id']!=oid]
    save(rows); return RedirectResponse('/',303)

@app.get('/health')
def health(): return {'ok':True,'service':'revenue-hunter-os','version':'0.4.0'}

def smtp_config():
    return {
        'host': os.getenv('PROTON_SMTP_HOST','127.0.0.1'),
        'port': int(os.getenv('PROTON_SMTP_PORT','1027')),
        'username': os.getenv('PROTON_SMTP_USERNAME',''),
        'password': os.getenv('PROTON_BRIDGE_PASSWORD',''),
        'from_email': os.getenv('PROTON_FROM_EMAIL', os.getenv('PROTON_SMTP_USERNAME','')),
        'from_name': os.getenv('PROTON_FROM_NAME','Shahzad Raza | Revenue Hunter OS'),
    }

def send_via_bridge(to_email, subject, body):
    c=smtp_config()
    if not c['username'] or not c['password']:
        raise RuntimeError('Proton Bridge credentials are not configured in .env')
    msg=EmailMessage()
    msg['From']=f"{c['from_name']} <{c['from_email']}>"
    msg['To']=to_email
    msg['Subject']=subject
    msg.set_content(body)
    ctx=ssl.create_default_context()
    # Proton Bridge presents a local certificate; TLS is still used locally.
    ctx.check_hostname=False
    ctx.verify_mode=ssl.CERT_NONE
    with smtplib.SMTP(c['host'], c['port'], timeout=20) as server:
        server.starttls(context=ctx)
        server.login(c['username'], c['password'])
        server.send_message(msg)

@app.post('/opportunities/{oid}/send')
def send_email(oid:str, to_email:str=Form(...), subject:str=Form(...)):
    rows=load()
    for r in rows:
        if r['id']==oid:
            send_via_bridge(to_email, subject, r['pitch'])
            r['status']='Pitched'
            r['contact_email']=to_email
            r['sent_at']=datetime.utcnow().isoformat(timespec='seconds')
            save(rows)
            return RedirectResponse('/',303)
    return JSONResponse({'ok':False,'error':'Opportunity not found'},status_code=404)

@app.get('/api/mail/status')
def mail_status():
    c=smtp_config()
    return {'configured':bool(c['username'] and c['password']), 'host':c['host'], 'port':c['port'], 'from_email':c['from_email']}
