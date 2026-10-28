"""Copy available desktop artifacts to private R2; retain every source file."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.postgres import PostgresConnection
from app.storage import publish_artifact,validate_key

def migrate():
    os.environ['STORAGE_BACKEND']='r2'
    root=Path.cwd().resolve();conn=PostgresConnection(get_settings().database_url)
    uploaded=[];missing=[]
    try:
        for row in conn.execute('SELECT * FROM artifact_objects').fetchall():
            key=validate_key(row['object_key']);source=root/'data/artifacts'/key
            if source.is_file():
                publish_artifact(conn,key,source,run_id=row['run_id'],business_id=row['business_id'],kind=row['kind']);uploaded.append(key)
            else:missing.append(key)
        for row in conn.execute('SELECT id,output_file FROM pipeline_runs WHERE output_file IS NOT NULL').fetchall():
            source=Path(row['output_file']).resolve()
            if not source.is_relative_to(root):continue
            for kind in ('xlsx','csv'):
                file=source.with_suffix('.'+kind)
                if file.is_file():
                    key=f"campaigns/legacy-run-{row['id']}/leads.{kind}"
                    publish_artifact(conn,key,file,run_id=row['id'],kind=kind);uploaded.append(key)
        for file in (root/'output/reports').glob('*.html'):
            raw=file.name.split('_',1)[0]
            if not raw.isdigit():continue
            bid=int(raw)
            if not conn.execute('SELECT id FROM businesses WHERE id=?',(bid,)).fetchone():continue
            key=f'prospects/{bid}/reports/report.html'
            publish_artifact(conn,key,file,business_id=bid,kind='html');uploaded.append(key)
        conn.commit()
        report={'uploaded':len(uploaded),'keys':uploaded,'source_files_missing':missing,'source_preserved':True}
        Path('docs/artifact-migration.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({'uploaded':len(uploaded),'source_files_missing':len(missing)}))
    finally:conn.close()

if __name__=='__main__':migrate()
