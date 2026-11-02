"""نمونهٔ اولیهٔ شفاف CRL؛ بدون مدل زبانی یا وابستگی بیرونی."""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import json
import sqlite3
from dataclasses import dataclass
import hashlib
import itertools
import re
from typing import Iterable
from pathlib import Path

# فهرست کوچک و قابل بازبینی است؛ حذف واژه‌ها فقط برای تطبیق است، نه از متن خام.
STOPWORDS = frozenset("""
و یا از به در با برای که را این آن یک است هستند بود بودند شد شده می شود کنند کردن
ها های اش شان من تو او ما شما آنها چه چیزی کی کجا چرا چگونه آیا اگر اما تا هم نیز
بر علیه بدون درباره توسط زیرا چون هست نیست دارند دارد انجام میدهند میکنند میکند می‌شود
the a an and or of to in on for is are was were be with this that what which who where
why how do does did can could would should it its as by from
""".split())
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?؟؛])\s+|[\r\n]+')
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_TRANSLATE = str.maketrans({'ي':'ی', 'ى':'ی', 'ك':'ک'})


def canonicalize(text: str) -> str:
    """یکسان‌سازی حروف عربی/فارسی و حذف نیم‌فاصله برای تطبیق واژه‌ها."""
    return text.translate(_TRANSLATE).replace('\u200c', '').replace('\u200d', '')


def tokenize(text: str, *, matching: bool = False) -> list[str]:
    words = [w.lower() for w in _TOKEN.findall(canonicalize(text))]
    return [w for w in words if w not in STOPWORDS] if matching else words


@dataclass(frozen=True)
class SentenceRecord:
    text: str
    source: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class Fact:
    subject: str
    relation: str
    object: str
    source: str
    sentence: str


class CRL:
    """ذخیره‌ساز کوچک درون‌حافظه‌ای برای شاهد متنی، گراف هم‌رخدادی و پاسخ استخراجی."""
    def __init__(self) -> None:
        self.sentences: list[SentenceRecord] = []
        self._sentence_keys: set[tuple[str, str]] = set()
        self.edges: dict[tuple[str, str], int] = {}
        self._adj: dict[str, Counter[str]] = defaultdict(Counter)
        self.facts: list[Fact] = []

    def ingest_text(self, document: str, source: str = 'نامشخص') -> int:
        """جمله‌ها را نگه می‌دارد و یال‌های هم‌رخدادی را افزایش می‌دهد؛ تعداد جدید را برمی‌گرداند."""
        added = 0
        for part in _SENTENCE_SPLIT.split(document):
            sentence = part.strip()
            if not sentence:
                continue
            key = (source, sentence)
            if key in self._sentence_keys:
                continue
            self._sentence_keys.add(key)
            tokens = tuple(tokenize(sentence, matching=True))
            self.sentences.append(SentenceRecord(sentence, source, tokens))
            added += 1
            # هر جفت واژهٔ متمایز در یک جمله یک بار شمرده می‌شود؛ یال خودی ساخته نمی‌شود.
            for left, right in itertools.combinations(sorted(set(tokens)), 2):
                edge = (left, right)
                self.edges[edge] = self.edges.get(edge, 0) + 1
                self._adj[left][right] += 1
                self._adj[right][left] += 1
        return added

    def learn_fact(self, subject: str, relation: str, object: str,
                   source: str = 'واقعیت صریح') -> Fact:
        """سه‌تایی را فقط با درخواست صریح ثبت می‌کند؛ استخراج سه‌تایی از متن انجام نمی‌شود."""
        subject, relation, object = (x.strip() for x in (subject, relation, object))
        if not subject or not relation or not object:
            raise ValueError('فاعل، رابطه و مفعول باید خالی نباشند.')
        sentence = f'{subject} {relation} {object}.'
        fact = Fact(subject, relation, object, source, sentence)
        self.facts.append(fact)
        self.ingest_text(sentence, source=source)
        return fact

    @staticmethod
    def coordinates(term: str) -> tuple[float, float, float]:
        """مختصات نمایشی پایدار در بازهٔ [-1,1]؛ فاقد معنای فیزیکی/معنایی."""
        digest = hashlib.sha256(canonicalize(term).encode('utf-8')).digest()
        return tuple(round(int.from_bytes(digest[i:i+4], 'big') / (2**32-1) * 2 - 1, 6)
                     for i in (0, 4, 8))  # type: ignore[return-value]

    def related(self, term: str, limit: int = 10) -> list[tuple[str, int]]:
        """رتبه‌بندی همسایه‌های گراف تا دو گام؛ صرفاً سرنخ ساختاری، نه شاهد پاسخ."""
        if limit <= 0:
            return []
        start = tokenize(term, matching=True)
        if not start:
            return []
        origin = start[0]
        scores: Counter[str] = Counter()
        for neighbor, weight in self._adj.get(origin, {}).items():
            scores[neighbor] += weight
            for second, w2 in self._adj.get(neighbor, {}).items():
                if second != origin:
                    scores[second] += min(weight, w2) / 2
        scores.pop(origin, None)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]

    def _rank(self, question: str) -> list[tuple[tuple[float, int, float], SentenceRecord, tuple[str, ...]]]:
        query = set(tokenize(question, matching=True))
        if not query:
            return []
        ranked = []
        for record in self.sentences:
            hits = tuple(sorted(query.intersection(record.tokens)))
            if not hits:
                continue
            coverage = len(hits) / len(query)
            # اشتراک واژگانی و پوشش سؤال؛ هندسهٔ مختصات اصلاً دخیل نیست.
            score = (coverage, len(hits), len(hits) / max(1, len(set(record.tokens))))
            ranked.append((score, record, hits))
        return sorted(ranked, key=lambda x: (tuple(-v for v in x[0]), x[1].source, x[1].text))

    def ask(self, question: str) -> str:
        """شاهد متنی را بازیابی می‌کند؛ پاسخ معنایی تولید نمی‌کند و در شواهد ناکافی رد می‌کند."""
        query = set(tokenize(question, matching=True))
        ranked = self._rank(question)
        # برای پرسش چندواژه‌ای، یک اشتراک منفرد کافی نیست؛ پوشش نیز باید دست‌کم نصف باشد.
        if not ranked or (len(query) >= 2 and
                          (len(ranked[0][2]) < 2 or ranked[0][0][0] < 0.5)):
            return 'شاهد متنیِ کافی پیدا نشد؛ نمی‌توانم با اطمینان پاسخ بدهم.'
        _, record, hits = ranked[0]
        matched = '، '.join(hits)
        return (f'یک جملهٔ مرتبط بازیابی شد (واژه‌های مشترک: {matched})؛ '
                f'این بازیابی به‌تنهایی پاسخ معنایی یا تأیید حقیقت نیست. '
                f'شاهد: «{record.text}» (منبع: {record.source}).')

    def _state_dict(self) -> dict:
        return {'schema_version': 1, 'sentences': [{'text': r.text, 'source': r.source} for r in self.sentences], 'facts': [{'subject': f.subject, 'relation': f.relation, 'object': f.object, 'source': f.source, 'sentence': f.sentence} for f in self.facts]}
    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self._state_dict(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    @classmethod
    def load_json(cls, path: str | Path) -> 'CRL':
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('sentences'),list) or not isinstance(data.get('facts'),list): raise ValueError('نسخه یا ساختار فایل CRL پشتیبانی نمی‌شود.')
        obj=cls()
        for r in data['sentences']:
            if not isinstance(r,dict) or not isinstance(r.get('text'),str) or not isinstance(r.get('source'),str): raise ValueError('رکورد جمله نامعتبر است.')
            obj.ingest_text(r['text'],r['source'])
        for f in data['facts']:
            if not isinstance(f,dict) or not all(isinstance(f.get(k),str) for k in ('subject','relation','object','source','sentence')): raise ValueError('رکورد واقعیت نامعتبر است.')
            obj.facts.append(Fact(f['subject'],f['relation'],f['object'],f['source'],f['sentence']))
        return obj
    def save_sqlite(self, path: str | Path) -> None:
        with sqlite3.connect(str(path)) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS sentences (id INTEGER PRIMARY KEY, text TEXT NOT NULL, source TEXT NOT NULL); CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, subject TEXT NOT NULL, relation TEXT NOT NULL, object TEXT NOT NULL, source TEXT NOT NULL, sentence TEXT NOT NULL);')
            with db:
                db.execute('DELETE FROM metadata'); db.execute('DELETE FROM sentences'); db.execute('DELETE FROM facts')
                db.execute('INSERT INTO metadata VALUES (?,?)',('schema_version','1'))
                db.executemany('INSERT INTO sentences(text,source) VALUES (?,?)',[(r.text,r.source) for r in self.sentences])
                db.executemany('INSERT INTO facts(subject,relation,object,source,sentence) VALUES (?,?,?,?,?)',[(f.subject,f.relation,f.object,f.source,f.sentence) for f in self.facts])
    @classmethod
    def load_sqlite(cls,path: str | Path)->'CRL':
        with sqlite3.connect(str(path)) as db:
            v=db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if v is None or v[0]!='1': raise ValueError('نسخهٔ SQLite پشتیبانی نمی‌شود.')
            sentences=db.execute('SELECT text,source FROM sentences ORDER BY id').fetchall(); facts=db.execute('SELECT subject,relation,object,source,sentence FROM facts ORDER BY id').fetchall()
        obj=cls()
        for t,sr in sentences: obj.ingest_text(t,sr)
        obj.facts=[Fact(*f) for f in facts]
        return obj
    def export_graph_json(self,path: str | Path | None=None)->dict:
        terms=sorted({t for e in self.edges for t in e})
        g={'schema_version':1,'nodes':[{'id':t,'label':t,'x':self.coordinates(t)[0],'y':self.coordinates(t)[1],'z':self.coordinates(t)[2]} for t in terms], 'edges':[{'source':a,'target':b,'weight':w} for (a,b),w in sorted(self.edges.items())]}
        if path is not None: Path(path).write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return g
    def export_graph_html(self,path: str | Path)->None:
        graph=json.dumps(self.export_graph_json(),ensure_ascii=False).replace('</','<\\/')
        page='''<!doctype html><html lang="fa"><meta charset="utf-8"><title>CRL Offline Graph</title><style>body{margin:0;background:#101827;color:white;font:16px sans-serif}canvas{width:100vw;height:90vh;touch-action:none}</style><header>گراف سه‌بعدی CRL آفلاین — کشیدن برای چرخش، چرخ‌موش برای بزرگ‌نمایی</header><canvas id="g"></canvas><script>const G=__G__,c=document.getElementById("g"),x=c.getContext("2d");let yaw=0,pitch=0,scale=1,drag=null;function draw(){let d=devicePixelRatio||1;c.width=innerWidth*d;c.height=innerHeight*.9*d;x.setTransform(d,0,0,d,0,0);x.clearRect(0,0,innerWidth,innerHeight);let P=new Map;for(const n of G.nodes){let a=n.x*Math.cos(yaw)-n.z*Math.sin(yaw),z=n.x*Math.sin(yaw)+n.z*Math.cos(yaw),b=n.y*Math.cos(pitch)-z*Math.sin(pitch),dep=n.y*Math.sin(pitch)+z*Math.cos(pitch),k=180*scale/(3+dep);P.set(n.id,{x:innerWidth/2+a*k,y:innerHeight*.42-b*k})}for(const e of G.edges){let a=P.get(e.source),b=P.get(e.target);x.strokeStyle="#52657e";x.beginPath();x.moveTo(a.x,a.y);x.lineTo(b.x,b.y);x.stroke()}for(const n of G.nodes){let p=P.get(n.id);x.fillStyle="#60d5c4";x.beginPath();x.arc(p.x,p.y,5,0,7);x.fill();x.fillStyle="white";x.fillText(n.label,p.x+7,p.y-5)}}c.onpointerdown=e=>{drag=[e.clientX,e.clientY];c.setPointerCapture(e.pointerId)};c.onpointerup=()=>drag=null;c.onpointermove=e=>{if(drag){yaw+=(e.clientX-drag[0])*.008;pitch+=(e.clientY-drag[1])*.008;drag=[e.clientX,e.clientY];draw()}};c.onwheel=e=>{scale=Math.max(.3,Math.min(4,scale*(e.deltaY<0?1.1:.9)));draw();e.preventDefault()};onresize=draw;draw();</script></html>'''.replace('__G__',graph)
        Path(path).write_text(page,encoding='utf-8')

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description='CRL persistence and graph export CLI')
    load_group = parser.add_mutually_exclusive_group()
    load_group.add_argument('--load-json', help='بارگذاری پایگاه CRL از JSON')
    load_group.add_argument('--load-sqlite', help='بارگذاری پایگاه CRL از SQLite')
    for opt in ('input','ask','save-json','save-sqlite','export-json','export-html'):
        parser.add_argument('--'+opt)
    parser.add_argument('--source',default='CLI'); args=parser.parse_args(argv)
    if args.load_json:
        c=CRL.load_json(args.load_json)
    elif args.load_sqlite:
        c=CRL.load_sqlite(args.load_sqlite)
    else:
        c=CRL()
    if args.input: c.ingest_text(Path(args.input).read_text(encoding='utf-8'),args.source)
    if args.ask: print(c.ask(args.ask))
    if args.save_json: c.save_json(args.save_json)
    if args.save_sqlite: c.save_sqlite(args.save_sqlite)
    if args.export_json: c.export_graph_json(args.export_json)
    if args.export_html: c.export_graph_html(args.export_html)
    return 0
if __name__=='__main__': raise SystemExit(main())
