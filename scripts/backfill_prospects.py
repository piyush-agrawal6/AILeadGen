"""Batch canonical identity backfill preserving every historical business row."""
import json
import sys
import uuid
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.postgres import PostgresConnection
from app.database.repositories import BusinessRepository
from app.database.prospects import identity_keys,now


def backfill(conn):
    repo=BusinessRepository(conn)
    known={row[0]:row[1] for row in conn.execute("SELECT identity_key,prospect_id FROM business_identities").fetchall()}
    rows=conn.execute("SELECT * FROM businesses WHERE is_rejected=0 ORDER BY id").fetchall()
    new_prospects={};identities={};links=[];observations={};aliases={};bridges=[]
    def canonical(pid):
        while pid in aliases:pid=aliases[pid]
        return pid
    for row in rows:
        b=repo._row_to_business(row);keys=identity_keys(b)
        matched={canonical(known[key]) for key,_ in keys if key in known}
        if row["prospect_id"]:matched.add(row["prospect_id"])
        if len(matched)>1:
            # Unite only groups created in this transaction, never persisted workflow.
            if not matched.issubset(new_prospects):
                raise ValueError(f"Conflicting persisted identities for business {b.id}; review before migration")
            winner=min(matched)
            for old in matched-{winner}:
                aliases[old]=winner
                previous=new_prospects.pop(old)
                new_prospects[winner][1]=min(new_prospects[winner][1],previous[1])
                new_prospects[winner][2]=max(new_prospects[winner][2],previous[2])
            bridges.append(b.id);matched={winner}
        pid=next(iter(matched),None) or str(uuid.uuid4())
        try:
            seen=datetime.fromisoformat(b.created_at or now())
            if seen.tzinfo is None:seen=seen.replace(tzinfo=timezone.utc)
            seen=seen.isoformat()
        except ValueError:seen=now()
        if not matched:new_prospects[pid]=[pid,seen,seen,now()]
        elif pid in new_prospects:
            new_prospects[pid][1]=min(new_prospects[pid][1],seen)
            new_prospects[pid][2]=max(new_prospects[pid][2],seen)
        for key,kind in keys:
            known[key]=pid;identities[key]=(key,pid,kind)
        links.append((pid,b.id))
        if b.run_id is not None:observations.setdefault((pid,b.run_id),(pid,b.run_id,b.id,seen))
    identities={key:(key,canonical(pid),kind) for key,pid,kind in identities.values()}
    links=[(canonical(pid),bid) for pid,bid in links]
    observations={(canonical(pid),rid):(canonical(pid),rid,bid,seen) for pid,rid,bid,seen in observations.values()}
    if new_prospects:conn.executemany("INSERT INTO prospects(id,first_seen_at,last_seen_at,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING",new_prospects.values())
    if identities:conn.executemany("INSERT INTO business_identities(identity_key,prospect_id,evidence_type) VALUES(?,?,?) ON CONFLICT(identity_key) DO NOTHING",identities.values())
    if links:conn.executemany("UPDATE businesses SET prospect_id=? WHERE id=?",links)
    if observations:conn.executemany("INSERT INTO prospect_observations(prospect_id,run_id,business_id,observed_at) VALUES(?,?,?,?) ON CONFLICT(prospect_id,run_id) DO NOTHING",observations.values())
    conn.execute("UPDATE prospects SET times_discovered=CASE WHEN (SELECT COUNT(*) FROM prospect_observations o WHERE o.prospect_id=prospects.id)=0 THEN 1 ELSE (SELECT COUNT(*) FROM prospect_observations o WHERE o.prospect_id=prospects.id) END")
    conn.commit()
    report={"historical_business_rows":len(rows),"new_canonical_prospects":len(new_prospects),"identity_keys":len(identities),"linked_observations":len(observations),"historical_evidence_bridges":bridges,"workflow_preserved":True}
    return report


if __name__=="__main__":
    conn=PostgresConnection(get_settings().database_url)
    try:
        report=backfill(conn)
        Path('docs/prospect-backfill.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
    except Exception:
        conn.rollback();raise
    finally:conn.close()
