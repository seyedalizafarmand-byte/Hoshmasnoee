"""Local Flask dashboard for CRL. Run: python crl_ui.py"""
from __future__ import annotations
import argparse, io, json, tempfile
from pathlib import Path
from threading import RLock
from flask import Flask, jsonify, render_template_string, request, send_file
from crl import CRL
app=Flask(__name__); app.config['MAX_CONTENT_LENGTH']=2*1024*1024
crl=CRL(); lock=RLock()
PAGE=r'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CRL | دانش نگار</title>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/dist/vis-network.min.css"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-graph3d/7.1.0/vis-graph3d.min.css">
<style>:root{--bg:#080b13;--panel:rgba(20,26,40,.78);--line:#94a3b824;--txt:#e8edf8;--muted:#8c98ae;--cyan:#59e1df;--violet:#a997ff;--green:#73e6ae}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% -10%,#192443,transparent 42%),radial-gradient(ellipse at 0 60%,#132b34,transparent 35%),var(--bg);color:var(--txt);font-family:Vazirmatn,system-ui,sans-serif}.shell{max-width:1500px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.brand{display:flex;align-items:center;gap:13px}.logo{height:46px;width:46px;border-radius:15px;background:linear-gradient(140deg,#52ded8,#866cff);display:grid;place-items:center;color:#071017;font-size:22px;font-weight:900;box-shadow:0 8px 35px #52ded833}.brand h1{font-size:19px;margin:0}.brand small,.muted{color:var(--muted)}.brand small{font-size:12px}.pill{border:1px solid var(--line);border-radius:99px;padding:8px 12px;color:#c0cad9;font-size:12px;background:#ffffff08}.dot{display:inline-block;width:8px;height:8px;border-radius:10px;background:var(--green);margin-left:7px;box-shadow:0 0 12px var(--green)}.grid{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(310px,.85fr);gap:18px}.maincol,.sidecol{display:flex;flex-direction:column;gap:18px}.panel{background:var(--panel);border:1px solid var(--line);backdrop-filter:blur(18px);border-radius:19px;box-shadow:0 16px 60px #0003}.head{padding:18px 20px 0;display:flex;align-items:center;justify-content:space-between}.head h2,.section h3{font-size:15px;margin:0}.sub,.section p{color:var(--muted);font-size:12px;margin:4px 0}.chat{height:410px;display:flex;flex-direction:column}.messages{padding:18px 20px;overflow:auto;flex:1;display:flex;flex-direction:column;gap:12px}.msg{max-width:88%;padding:12px 14px;border-radius:15px;line-height:1.85;font-size:13px;white-space:pre-wrap}.msg.system{align-self:flex-start;background:#ffffff0a;border:1px solid var(--line);color:#cbd5e1}.msg.user{align-self:flex-end;background:linear-gradient(130deg,#294e65,#31305c)}.badge{display:inline-flex;border-radius:99px;padding:3px 8px;font-size:10px;margin-bottom:7px}.lex{background:#123b3b;color:#72e7da}.gen{background:#382b52;color:#c5afff}.inputrow{display:flex;gap:9px;padding:14px 16px;border-top:1px solid var(--line)}input{font:inherit;color:var(--txt);background:#0a0e18;border:1px solid var(--line);border-radius:11px;padding:11px 12px;outline:none}input:focus{border-color:#59e1df88}#question{flex:1}button{font:inherit;cursor:pointer;border:1px solid var(--line);background:#ffffff0a;color:var(--txt);border-radius:10px;padding:9px 13px}button:hover{border-color:#59e1df88;background:#59e1df14}.primary{background:linear-gradient(120deg,#42cfc9,#8c78ed);color:#061014;border:0;font-weight:700}.graphbox{height:365px;margin:15px;border-radius:14px;background:#0a0e17;overflow:hidden}.graphbox>div{height:100%;width:100%}#graph3d{display:none}.toggle{display:flex;gap:6px}.active{background:#57dcd522;border-color:#57dcd588;color:#7ceddf}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:17px}.stat{padding:13px;border-radius:13px;background:#ffffff06;border:1px solid var(--line)}.stat strong{display:block;font-size:22px;color:#d8e6ff}.stat span,.field label{font-size:11px;color:var(--muted)}.section{padding:17px 19px}.field{display:flex;flex-direction:column;gap:7px;margin:10px 0}.field input{width:100%;font-size:12px}.upload{padding:12px;border:1px dashed #8491ab55;border-radius:13px;text-align:center;color:var(--muted);font-size:12px}.upload input{max-width:100%;margin-top:10px}.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.note{font-size:11px;color:#a7b2c5;line-height:1.9;padding:12px;border:1px solid #d6b76422;background:#d6b76408;border-radius:12px}.status{font-size:11px;color:var(--muted);min-height:18px;margin-top:8px}.footer{text-align:center;color:#617087;font-size:11px;padding:18px}@media(max-width:900px){.grid{grid-template-columns:1fr}.sidecol{display:grid;grid-template-columns:1fr 1fr}}@media(max-width:620px){.sidecol{display:flex}.shell{padding:13px}.top{align-items:flex-start;gap:8px}.pill{font-size:10px}.graphbox{height:310px}}</style></head><body><div class="shell"><header class="top"><div class="brand"><div class="logo">◈</div><div><h1>دانش نگار <span style="color:var(--cyan)">CRL</span></h1><small>فضای محلی برای بازیابی شواهد و اکتشاف دانش</small></div></div><div class="pill"><span class="dot"></span>هسته محلی فعال · بدون مدل مولد</div></header><div class="grid"><main class="maincol">
<section class="panel chat"><div class="head"><div><h2>گفت و گوی دانشی</h2><div class="sub">پرسش از اسناد و واقعیت های ثبت شده</div></div><span class="badge lex">LEXICAL RETRIEVAL</span></div><div class="messages" id="messages"><div class="msg system"><span class="badge lex">بازیابی واژگانی</span><br>سلام! پرسشت را بپرس. پاسخ ها فقط شواهد متنی دارای منبع را بازیابی می کنند؛ این سامانه پاسخ مولد یا تایید حقیقت نیست.</div></div><form class="inputrow" id="askForm"><input id="question" placeholder="مثلا: گیاهان چه چیزی جذب می کنند؟" autocomplete="off"><button class="primary">پرسیدن ↵</button></form></section>
<section class="panel"><div class="head"><div><h2>نقشه هم رخدادی</h2><div class="sub">ساختار واژه ها، نه روابط معنایی</div></div><div class="toggle"><button id="btn2d" class="active" onclick="setView('2d')">۲بعدی</button><button id="btn3d" onclick="setView('3d')">۳بعدی</button></div></div><div class="graphbox"><div id="graph2d"></div><div id="graph3d"></div></div><div class="sub" style="padding:0 20px 17px">یال ها نشان دهنده هم رخدادی در جمله اند؛ مختصات سه بعدی فقط نمایشی هستند.</div></section></main>
<aside class="sidecol"><section class="panel"><div class="head"><div><h2>وضعیت حافظه</h2><div class="sub">شاخص های پایگاه دانش جاری</div></div></div><div class="stats"><div class="stat"><strong id="sentCount">۰</strong><span>جمله</span></div><div class="stat"><strong id="factCount">۰</strong><span>واقعیت صریح</span></div><div class="stat"><strong id="nodeCount">۰</strong><span>گره</span></div></div></section>
<section class="panel section"><h3>ورود سند</h3><p>فایل متنی UTF-8 را به حافظه محلی اضافه کن.</p><div class="upload">فایل .txt یا .md<input type="file" id="docFile" accept=".txt,.md,text/plain,text/markdown"></div><div class="field"><label>نام منبع</label><input id="docSource" placeholder="مثلا: یادداشت جلسه"></div><button class="primary" style="width:100%" onclick="ingest()">افزودن به دانش</button><div class="status" id="ingestStatus"></div></section>
<section class="panel section"><h3>ثبت واقعیت صریح</h3><p>سه تایی فقط به درخواست تو ثبت می شود؛ از متن استخراج نمی شود.</p><div class="field"><label>فاعل</label><input id="subject" placeholder="آب"></div><div class="field"><label>رابطه</label><input id="relation" placeholder="برای رشد لازم است"></div><div class="field"><label>مفعول</label><input id="object" placeholder="گیاه"></div><div class="field"><label>منبع</label><input id="factSource" placeholder="واقعیت صریح"></div><button class="primary" style="width:100%" onclick="saveFact()">ثبت سه تایی</button><div class="status" id="factStatus"></div></section>
<section class="panel section"><h3>پایگاه داده</h3><p>فایل JSON یا SQLite؛ ذخیره، نسخه جاری را صادر می کند.</p><div class="actions"><button onclick="downloadDb('json')">ذخیره JSON</button><button onclick="downloadDb('sqlite')">ذخیره SQLite</button></div><div class="field"><label>بارگذاری پایگاه موجود</label><input type="file" id="dbFile" accept=".json,.sqlite,.db"></div><button style="width:100%" onclick="loadDb()">بارگذاری و جایگزینی حافظه</button><div class="status" id="dbStatus"></div></section><div class="note"><b>شفافیت مدل</b><br>هسته CRL از بازیابی واژگانی استفاده می کند؛ هیچ LLM، استنتاج معنایی یا فکت چک خودکاری فعال نیست. نشان بنفش جایگاه تولیدگر را توضیح می دهد، نه قابلیتی موجود.</div></aside></div><div class="footer">CRL · محلی و آزمایشی · فایل ها در همین دستگاه پردازش می شوند</div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.30.1/moment.min.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/vis-graph3d/7.1.0/vis-graph3d.min.js"></script><script>
const $=id=>document.getElementById(id);let network=null,graph3d=null,lastGraph=null;const fa=n=>new Intl.NumberFormat('fa-IR').format(n);function message(text,who='system'){const el=document.createElement('div');el.className='msg '+who;const b=document.createElement('span');b.className='badge lex';b.textContent='بازیابی واژگانی';el.append(b,document.createElement('br'),document.createTextNode(text));$('messages').append(el);$('messages').scrollTop=$('messages').scrollHeight}
$('askForm').addEventListener('submit',async e=>{e.preventDefault();let q=$('question').value.trim();if(!q)return;message(q,'user');$('question').value='';try{let r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})}),d=await r.json();message(d.answer)}catch(e){message('ارتباط با هسته برقرار نشد.')}});
async function refresh(){try{let [s,g]=await Promise.all([fetch('/api/stats').then(r=>r.json()),fetch('/api/graph').then(r=>r.json())]);$('sentCount').textContent=fa(s.sentences);$('factCount').textContent=fa(s.facts);$('nodeCount').textContent=fa(g.nodes.length);lastGraph=g;draw2d(g);if(graph3d)draw3d(g)}catch(e){}}
function draw2d(g){if(!window.vis){$('graph2d').innerHTML='<div style="padding:30px;color:#94a3b8">برای رسم تعاملی گراف، CDN کتابخانه vis لازم است.</div>';return}let ns=new vis.DataSet(g.nodes.map(n=>({id:n.id,label:n.label,title:n.label,shape:'dot',size:12,color:{background:'#58d9d4',border:'#a9fff4'},font:{color:'#e3ecf7',face:'Vazirmatn'}})));let es=new vis.DataSet(g.edges.map((e,i)=>({id:i,from:e.source,to:e.target,value:e.weight,title:'هم رخدادی: '+e.weight,color:{color:'#7569b4',opacity:.6}})));if(network)network.destroy();network=new vis.Network($('graph2d'),{nodes:ns,edges:es},{physics:{stabilization:{iterations:120},barnesHut:{gravitationalConstant:-2200,springLength:115}},interaction:{hover:true,navigationButtons:true,keyboard:true},edges:{scaling:{min:1,max:6}}})}
function draw3d(g){if(!window.vis||!vis.Graph3d)return;$('graph3d').innerHTML='';let rows=g.nodes.map(n=>({x:n.x,y:n.y,z:n.z,style:12,label:n.label}));graph3d=new vis.Graph3d($('graph3d'),new vis.DataSet(rows),{width:'100%',height:'100%',style:'dot-color',showPerspective:true,showGrid:true,showXAxis:true,showYAxis:true,showZAxis:true,backgroundColor:{fill:'#0b101b',stroke:'#243148'},axisColor:'#8291a8',keepAspectRatio:true,tooltip:true})}
function setView(v){$('graph2d').style.display=v==='2d'?'block':'none';$('graph3d').style.display=v==='3d'?'block':'none';$('btn2d').classList.toggle('active',v==='2d');$('btn3d').classList.toggle('active',v==='3d');if(v==='3d'&&lastGraph)draw3d(lastGraph)}
async function ingest(){let f=$('docFile').files[0];if(!f){$('ingestStatus').textContent='ابتدا فایل متنی انتخاب کن.';return}let fd=new FormData();fd.append('file',f);fd.append('source',$('docSource').value||f.name);try{let r=await fetch('/api/ingest',{method:'POST',body:fd}),d=await r.json();$('ingestStatus').textContent=r.ok?fa(d.added)+' جمله افزوده شد.':d.error;if(r.ok)refresh()}catch(e){$('ingestStatus').textContent='خطای ارتباط'}}
async function saveFact(){let p={subject:$('subject').value,relation:$('relation').value,object:$('object').value,source:$('factSource').value||'واقعیت صریح'};let r=await fetch('/api/fact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}),d=await r.json();$('factStatus').textContent=r.ok?'واقعیت صریح ثبت شد.':d.error;if(r.ok)refresh()}
function downloadDb(fmt){location.href='/api/database/'+fmt}async function loadDb(){let f=$('dbFile').files[0];if(!f){$('dbStatus').textContent='یک فایل JSON یا SQLite انتخاب کن.';return}let fd=new FormData();fd.append('file',f);let r=await fetch('/api/load',{method:'POST',body:fd}),d=await r.json();$('dbStatus').textContent=r.ok?'پایگاه بارگذاری شد · '+fa(d.sentences)+' جمله':d.error;if(r.ok)refresh()}refresh();</script></body></html>'''
@app.get('/')
def home(): return render_template_string(PAGE)
@app.get('/api/stats')
def stats():
 with lock:return jsonify(sentences=len(crl.sentences),facts=len(crl.facts),edges=len(crl.edges))
@app.get('/api/graph')
def graph():
 with lock:return jsonify(crl.export_graph_json())
@app.post('/api/ask')
def ask():
 d=request.get_json(silent=True) or {};q=d.get('question')
 if not isinstance(q,str) or not q.strip():return jsonify(error='پرسش نمی تواند خالی باشد.'),400
 with lock:a=crl.ask(q)
 return jsonify(answer=a,mode='lexical_retrieval',generative=False)
@app.post('/api/ingest')
def ingest():
 f=request.files.get('file')
 if not f or not f.filename:return jsonify(error='فایل انتخاب نشده است.'),400
 if Path(f.filename).suffix.lower() not in {'.txt','.md'}:return jsonify(error='فقط .txt و .md پشتیبانی می شوند.'),415
 try:text=f.read().decode('utf-8-sig')
 except UnicodeDecodeError:return jsonify(error='فایل باید UTF-8 باشد.'),400
 if not text.strip():return jsonify(error='فایل خالی است.'),400
 source=request.form.get('source','').strip() or Path(f.filename).name
 with lock:n=crl.ingest_text(text,source)
 return jsonify(added=n,source=source)
@app.post('/api/fact')
def fact():
 d=request.get_json(silent=True) or {}
 try:
  with lock:f=crl.learn_fact(d.get('subject',''),d.get('relation',''),d.get('object',''),d.get('source') or 'واقعیت صریح')
 except (ValueError,AttributeError) as e:return jsonify(error=str(e)),400
 return jsonify(fact={'subject':f.subject,'relation':f.relation,'object':f.object,'source':f.source})
@app.get('/api/database/<fmt>')
def download_db(fmt):
 if fmt not in ('json','sqlite'):return jsonify(error='قالب نامعتبر است.'),404
 ext='.json' if fmt=='json' else '.sqlite'
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/('crl_state'+ext)
  with lock:(crl.save_json if fmt=='json' else crl.save_sqlite)(path);raw=path.read_bytes()
 return send_file(io.BytesIO(raw),mimetype='application/json' if fmt=='json' else 'application/vnd.sqlite3',as_attachment=True,download_name='crl_state'+ext)
@app.post('/api/load')
def load_db():
 global crl
 f=request.files.get('file')
 if not f or not f.filename:return jsonify(error='فایل انتخاب نشده است.'),400
 ext=Path(f.filename).suffix.lower()
 if ext not in {'.json','.sqlite','.db'}:return jsonify(error='فقط JSON یا SQLite پشتیبانی می شود.'),415
 try:
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/('incoming'+ext);path.write_bytes(f.read());loaded=CRL.load_json(path) if ext=='.json' else CRL.load_sqlite(path)
  with lock:crl=loaded
  return jsonify(sentences=len(loaded.sentences),facts=len(loaded.facts))
 except Exception as e:return jsonify(error='بارگذاری ناموفق: '+str(e)),400
@app.errorhandler(413)
def too_large(_):return jsonify(error='حداکثر اندازه فایل ۲ مگابایت است.'),413
def main():
 p=argparse.ArgumentParser(description='رابط محلی CRL');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=5000);a=p.parse_args();app.run(host=a.host,port=a.port,debug=False)
if __name__=='__main__':main()
