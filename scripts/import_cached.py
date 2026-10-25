"""Load the real Instagram captures bundled with this project into its data store."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rules', action='store_true', help='Extract supported facts directly from caption/OCR text without a model call')
args = parser.parse_args()
if args.rules:
    os.environ['AI_BACKEND'] = 'heuristic'

import ai
from storage import get_store

posts = json.loads((ROOT / 'data' / 'instagram_posts.json').read_text())
if isinstance(posts, dict):
    posts = posts.get('posts', [])
posts = ai.analyze(posts)
report = get_store().ingest_posts(posts, source_mode='cached')
print(json.dumps({'posts': len(posts), 'validated_event_proposals': sum(len(p.get('events', [])) for p in posts), 'extraction_modes': sorted({p.get('extraction_mode', '') for p in posts}), 'ingestion': report}, default=str), flush=True)
