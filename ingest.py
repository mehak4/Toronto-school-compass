"""Index reviewed source summaries; replace/expand them with licensed source text."""
import hashlib
import json
import os
from core import ROOT
from provider import embed

def ingest():
    import chromadb
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    # Character based baseline, explicitly not a token-count claim.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1800, chunk_overlap=200)
    records = json.loads((ROOT / 'data/corpus.json').read_text())
    chunks = []
    for record in records:
        for i, text in enumerate(splitter.split_text(record['text'])):
            metadata = {k: v for k, v in record.items() if k != 'text'}
            chunks.append((f"{record['id']}-{i}", text, metadata))
    if not chunks:
        raise RuntimeError('Corpus is empty.')
    vectors = embed([c[1] for c in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError('Embedding count mismatch.')
    client = chromadb.PersistentClient(path=str(ROOT / '.chroma'))
    name = 'schools-' + hashlib.sha256(json.dumps([records, os.environ['EMBEDDING_MODEL'], os.environ['MODEL_BASE_URL']]).encode()).hexdigest()[:16]
    collection = client.get_or_create_collection(name)
    collection.upsert(ids=[c[0] for c in chunks], documents=[c[1] for c in chunks],
                      metadatas=[c[2] for c in chunks], embeddings=vectors)
    (ROOT / '.index.json').write_text(json.dumps({'collection': name,
        'model': os.environ['EMBEDDING_MODEL'], 'base_url': os.environ['MODEL_BASE_URL']}))
    print(f'Indexed {len(chunks)} chunks from {len(records)} sources.')

if __name__ == '__main__':
    ingest()
