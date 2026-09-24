"""Run document extraction, then resume its durable human review checkpoint."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from uuid import uuid4

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from document_agent.document_loader import load_document
from document_agent.agent import ModelClient, build_agent_graph, initial_state, result_from_state
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command


def write_json(path, value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    temp.replace(path)


def save_artifacts(output, result):
    # Drafts/checkpoints are local working state, not approved exports.
    write_json(output/'draft.json',result)
    lines=['# Document action report',f"Status: {result['status']}",f"Reviewed chunks: {len(result['reviewed_chunks'])}/{result['total_chunks']}"]
    for item in result['items']:
        lines += [f"\n## Item — {item['location']} (chunk {item['chunk_id']})",'\n'.join('> '+line for line in item['quote'].splitlines()),f"Owner: {item['owner'] or 'Not specified'}; Due: {item['due_date'] or 'Not specified'}"]
    lines+=['\n## Extraction warnings']+result['warnings']
    (output/'draft.md').write_text('\n\n'.join(lines)+'\n')
    if result['status']=='approved':
        write_json(output/'result.json',result)
        (output/'report.md').write_text('\n\n'.join(lines)+'\n')
    write_json(output/'review.json',{'status':result['status'],'review':result.get('review')})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file',type=Path)
    source.add_argument('--resume',type=Path,help='Existing run directory awaiting human review')
    parser.add_argument('--decision',choices=['approve','reject'])
    parser.add_argument('--review-note',default='')
    parser.add_argument('--task',choices=['extract_action_items','extract_requirements'],default='extract_action_items')
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json'))
    parser.add_argument('--env-file',type=Path,default=Path(__file__).resolve().parents[1]/'.env')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--ingest-only',action='store_true')
    args=parser.parse_args()
    if args.resume and (not args.decision or args.ingest_only or args.output):
        parser.error('--resume requires --decision and cannot use --output or --ingest-only')
    if args.decision and not args.resume:
        parser.error('Review the saved draft first; --decision requires --resume')
    try:
        client=None
        if args.resume:
            output=args.resume
            meta=json.loads((output/'run.json').read_text())
            db=output/'checkpoint.sqlite'
            if not db.is_file():raise ValueError('No checkpoint database found')
            invocation=Command(resume={'decision':args.decision,'note':args.review_note})
        else:
            config=json.loads(args.config.read_text())
            document=load_document(args.file,config['chunk_chars'])
            if not args.ingest_only:
                from dotenv import load_dotenv
                load_dotenv(args.env_file,override=False)
                client=ModelClient(config)
                invocation=initial_state(document,args.task,client.mode,config['max_steps'])
            output=args.output or Path(__file__).parent/'outputs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            output.mkdir(parents=True,exist_ok=False)
            write_json(output/'document.json',document.to_dict())
            if args.ingest_only:
                print(f'Extracted {len(document.chunks)} chunks to {output}; no model calls.')
                return 0
            meta={'thread_id':str(uuid4()),'max_steps':config['max_steps'],'framework':'LangGraph'}
            write_json(output/'run.json',meta)
            db=output/'checkpoint.sqlite'
        with (output/'steps.jsonl').open('a') as trace, SqliteSaver.from_conn_string(str(db)) as saver:
            def log(event):
                trace.write(json.dumps(event,ensure_ascii=False)+'\n');trace.flush()
                print(f"Step {event['step']}: {event['action']} — {str(event['reason'])[:160]}",flush=True)
            graph=build_agent_graph(client,saver,log)
            graph_config={'configurable':{'thread_id':meta['thread_id']},'recursion_limit':meta['max_steps']*3+10}
            if args.resume:
                snapshot=graph.get_state(graph_config)
                if snapshot.values.get('status')!='awaiting_review' or snapshot.next!=('human_review',):
                    raise ValueError('This run is not awaiting review; decisions cannot be replayed')
            state=graph.invoke(invocation,graph_config)
            result=result_from_state(state)
        save_artifacts(output,result)
        print(f"Saved {len(result['items'])} draft items to {output} ({result['status']}).")
        if result['status']=='awaiting_review':
            print('Read draft.md, then use --resume RUN_DIRECTORY --decision approve or reject. No final export has been written.')
        return 0 if result['status'] in {'awaiting_review','approved','rejected'} else 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'Error: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
