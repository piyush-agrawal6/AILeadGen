"""Prepare a restricted blind review package or validate real human submissions.

No sources or AI providers are called. Inputs must be reviewed public excerpts.
Never put private customer data or credentials into a review package.
"""
import argparse,csv,io,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.growth_intelligence import evaluation as e

def load(path):return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Exclusive creation preserves frozen packages and already submitted labels.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False))

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    prepare=sub.add_parser('prepare');prepare.add_argument('--candidates',required=True);prepare.add_argument('--registration',required=True);prepare.add_argument('--output',required=True)
    review=sub.add_parser('validate-review');review.add_argument('--package',required=True);review.add_argument('--review',required=True)
    queue=sub.add_parser('adjudication-queue');queue.add_argument('--package',required=True);queue.add_argument('--review',action='append',required=True);queue.add_argument('--output',required=True)
    final=sub.add_parser('finalize');final.add_argument('--package',required=True);final.add_argument('--review',action='append',required=True);final.add_argument('--decision',required=True);final.add_argument('--output',required=True)
    score=sub.add_parser('score');score.add_argument('--package',required=True);score.add_argument('--corpus',required=True);score.add_argument('--predictions',required=True);score.add_argument('--assessment',required=True);score.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.action=='prepare':
        package=e.prepare(load(args.candidates)['cases'],load(args.registration));folder=Path(args.output)
        write(folder/'private-manifest.json',package);write(folder/'blind-cases.json',{'package_hash':package['package_hash'],'cases':e.blind_rows(package)})
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['id','title','excerpt','source_url','source_family','language','observed_at','retrieved_at','icps'])
        from app.growth_intelligence.exports import cell
        for row in e.blind_rows(package):writer.writerow([cell(json.dumps(value,ensure_ascii=False) if isinstance(value,list) else value) for value in row.values()])
        write(folder/'blind-cases.csv',stream.getvalue())
        template={'package_hash':package['package_hash'],'reviewer_id':'','independent_attestation':False,'model_outputs_not_seen':False,'labels':[{key:None for key in e.Label.model_fields}|{'id':case['id']} for case in package['cases']]}
        write(folder/'review-template.json',template)
        write(folder/'README.md','# Independent blind review\n\nGive each reviewer only blind-cases.json (or CSV), this template and the labeling instructions. Keep private-manifest.json, other reviewer labels and all AI outputs hidden until both independent submissions are locked. Unknown values must be labeled UNCERTAIN, never guessed. Exact evidence quotes are mandatory for commercial intent and claims. Use docs/INTENT_RADAR_HUMAN_REVIEW_GUIDE.md.\n\nPackage status: '+package['readiness']['status']+'\n\n'+'\n'.join('- '+x for x in package['readiness']['blockers'])+'\n')
        print(json.dumps(package['readiness']))
    elif args.action=='validate-review':
        result=e.validate_review(load(args.package),load(args.review));print(json.dumps({'status':'SUBMISSION_VALID_NOT_ACCEPTED','labels':len(result.labels)}))
    elif args.action=='score':
        from scripts.evaluate_intent_radar_quality import evaluate,wilson
        result=e.score(load(args.package),load(args.corpus),load(args.predictions),load(args.assessment),evaluate,wilson)
        write(args.output,result);print(json.dumps({'status':result['status'],'blockers':result['blockers']}))
    else:
        package=load(args.package);reviews=[load(path) for path in args.review]
        result=e.adjudication_queue(package,reviews) if args.action=='adjudication-queue' else e.finalize(package,reviews,load(args.decision))
        write(args.output,result);print(json.dumps({'status':result['status'],'cases':len(package['cases'])}))
if __name__=='__main__':main()
