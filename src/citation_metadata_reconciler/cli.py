import argparse,csv,difflib,json,re,sys
from pathlib import Path

def bib_entries(text):
    entries=[]; offset=0
    while True:
        match=re.search(r"@([A-Za-z]+)\s*([\{\(])",text[offset:])
        if not match: break
        start=offset+match.start(); opening=offset+match.end()-1; opener=text[opening]; closer="}" if opener=="{" else ")"
        depth=1; quoted=False; index=opening+1
        while index<len(text) and depth:
            char=text[index]
            if char=='"' and (index==0 or text[index-1]!="\\"): quoted=not quoted
            if not quoted:
                if char==opener: depth+=1
                elif char==closer: depth-=1
            index+=1
        if depth: raise ValueError("unclosed BibTeX entry")
        inner=text[opening+1:index-1]; comma=inner.find(",")
        if comma>=0:
            key=inner[:comma].strip(); body=inner[comma+1:]; fields={}; pos=0
            while pos<len(body):
                field=re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*",body[pos:])
                if not field: break
                name=field.group(1).casefold(); value_start=pos+field.end()
                if value_start>=len(body): break
                if body[value_start]=="{":
                    nest=1; end=value_start+1
                    while end<len(body) and nest:
                        if body[end]=="{": nest+=1
                        elif body[end]=="}": nest-=1
                        end+=1
                    value=body[value_start+1:end-1].strip()
                elif body[value_start]=='"':
                    end=value_start+1
                    while end<len(body) and (body[end]!='"' or body[end-1]=="\\"): end+=1
                    value=body[value_start+1:end].strip(); end=min(end+1,len(body))
                else:
                    end=body.find(",",value_start)
                    if end<0: end=len(body)
                    value=body[value_start:end].strip()
                fields[name]=value; pos=end
            entries.append((key,fields,text[start:index]))
        offset=index
    return entries

def parse(path):
    text=Path(path).read_text(encoding="utf-8-sig"); ext=Path(path).suffix.casefold()
    if ext==".json":
        obj=json.loads(text); rows=obj if isinstance(obj,list) else [obj]
        if not all(isinstance(x,dict) for x in rows): raise ValueError("CSL JSON must contain objects")
        return [{"source_record":r,"record":dict(r)} for r in rows]
    if ext==".ris":
        rows=[]; fields={}; raw=[]
        for line in text.splitlines():
            raw.append(line)
            if line.strip().upper()=="ER  -": rows.append((fields,"\n".join(raw))); fields={}; raw=[]; continue
            m=re.match(r"^([A-Z0-9]{2})\s+-\s+(.*)$",line)
            if m: fields.setdefault(m.group(1),[]).append(m.group(2))
        if fields: rows.append((fields,"\n".join(raw)))
        return [{"source_record":{"raw":raw},"record":{"id":str(i+1),"title":f.get("TI",f.get("T1",[""]))[0],"DOI":f.get("DO",[""])[0],"author":f.get("AU",[]),"issued":{"date-parts":[[int(f.get("PY",["0"])[0][:4])]]} if f.get("PY",[""])[0][:4].isdigit() else {},"_ris_fields":f}} for i,(f,raw) in enumerate(rows)]
    if ext==".bib":
        rows=[]
        for key,fields,raw in bib_entries(text):
            rows.append({"source_record":{"citekey":key,"raw":raw},"record":{"id":key,"title":fields.get("title",""),"DOI":fields.get("doi",""),"author":fields.get("author",""),"issued":{"date-parts":[[int(fields["year"][:4])]]} if fields.get("year","")[:4].isdigit() else {},"_bibtex_fields":fields}})
        if not rows and text.strip(): raise ValueError("no BibTeX records parsed")
        return rows
    raise ValueError("supported formats: .bib, .ris, .json")

def doi_value(rec): return rec.get("DOI",rec.get("doi",""))
def valid_doi(value): return not value or bool(re.fullmatch(r"10\.\d{4,9}/\S+",str(value).strip(),re.I))
def has_year(rec):
    if rec.get("year"):
        return bool(re.fullmatch(r"\d{4}",str(rec["year"]).strip()))
    parts=rec.get("issued",{}).get("date-parts",[]) if isinstance(rec.get("issued"),dict) else []
    return bool(parts and isinstance(parts[0],list) and parts[0] and isinstance(parts[0][0],int) and parts[0][0]>0)
def validate(rec):
    errors=[]
    if not isinstance(rec.get("title"),str) or not rec["title"].strip(): errors.append("missing title")
    if not rec.get("author"): errors.append("missing author")
    if not has_year(rec): errors.append("missing or invalid publication year")
    doi=doi_value(rec)
    if doi and not valid_doi(doi): errors.append("invalid DOI syntax")
    return errors

def title_norm(s): return " ".join(re.findall(r"[a-z0-9]+",str(s).casefold()))
def rank_candidates(record,candidates):
    out=[]
    for c in candidates:
        if not isinstance(c,dict): continue
        d1=re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)","",str(doi_value(record)),flags=re.I).casefold(); d2=re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)","",str(doi_value(c)),flags=re.I).casefold()
        left,right=title_norm(record.get("title","")),title_norm(c.get("title",""))
        score=1.0 if d1 and d1==d2 else difflib.SequenceMatcher(None,left,right).ratio() if left and right else 0.0
        out.append({"candidate":c,"confidence":round(score,3)})
    return sorted(out,key=lambda x:(-x["confidence"],str(x["candidate"].get("id",""))))

def apply_mappings(records,candidates,mappings):
    by_id={str(c.get("id")):c for c in candidates if isinstance(c,dict) and c.get("id") is not None}; result=[]
    for item in records:
        record=dict(item["record"]); mapping=mappings.get(str(record.get("id","")))
        applied=False
        if mapping is not None:
            if not isinstance(mapping,dict) or mapping.get("confirm") is not True: raise ValueError(f"mapping for {record.get('id')} requires confirm: true")
            cid=str(mapping.get("candidate_id",""))
            if cid not in by_id: raise ValueError(f"unknown candidate id {cid}")
            candidate=by_id[cid]; record.update({k:v for k,v in candidate.items() if k not in ("id",) and (k not in record or not record[k])}); applied=True
        result.append({"source_record":item["source_record"],"record":record,"validation":validate(record),"mapping_applied":applied})
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description="Validate citations and inspect explicit metadata candidates")
    p.add_argument("input"); p.add_argument("--candidates",help="user-supplied JSON array/object fixture"); p.add_argument("--mapping",help="JSON object mapping record IDs to {candidate_id, confirm:true}"); p.add_argument("--output",help="write JSON report; stdout otherwise")
    a=p.parse_args(argv)
    try:
        rows=parse(a.input); candidates=[]
        if a.candidates:
            obj=json.loads(Path(a.candidates).read_text(encoding="utf-8")); candidates=obj if isinstance(obj,list) else obj.get("candidates",[])
            if not isinstance(candidates,list): raise ValueError("candidate fixture must contain an array")
        mappings=json.loads(Path(a.mapping).read_text(encoding="utf-8")) if a.mapping else {}
        if not isinstance(mappings,dict): raise ValueError("mapping must be a JSON object")
        records=apply_mappings(rows,candidates,mappings)
        report=[]
        for item in records:
            item["candidates"]=rank_candidates(item["record"],candidates); report.append(item)
        text=json.dumps({"records":report,"summary":{"records":len(report),"invalid":sum(bool(x["validation"]) for x in report),"mappings_applied":sum(x["mapping_applied"] for x in report)}},ensure_ascii=False,indent=2)+"\n"
        Path(a.output).write_text(text,encoding="utf-8",newline="\n") if a.output else sys.stdout.write(text)
        return 1 if any(x["validation"] for x in report) else 0
    except (OSError,json.JSONDecodeError,ValueError) as e: print(f"error: {e}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
