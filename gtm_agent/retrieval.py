"""Ephemeral Chroma vector store with query provenance; no shared persistent corpus."""
from uuid import uuid4
import chromadb

def retrieve(chunks,queries,model,top_k=4,max_evidence=12):
    if not chunks:raise ValueError('No document chunks to search')
    client=chromadb.EphemeralClient()
    name='campaign-'+uuid4().hex
    collection=client.create_collection(name,embedding_function=None,metadata={'hnsw:space':'cosine'})
    try:
        vectors=model.embed([c['text'] for c in chunks])
        collection.add(ids=[str(c['id']) for c in chunks],documents=[c['text'] for c in chunks],embeddings=vectors,
                       metadatas=[{'location':c['location']} for c in chunks])
        query_vectors=model.embed(queries)
        selected={}
        # Merge rank-by-rank so each planner query gets representation.
        results=[collection.query(query_embeddings=[v],n_results=min(top_k,len(chunks))) for v in query_vectors]
        for rank in range(min(top_k,len(chunks))):
            for query,res in zip(queries,results):
                sid=res['ids'][0][rank]
                if sid not in selected and len(selected)<max_evidence:
                    selected[sid]={'id':len(selected)+1,'chunk_id':int(sid),'location':res['metadatas'][0][rank]['location'],
                                   'text':res['documents'][0][rank],'retrieved_for':query}
        # For short briefs, retain every source so dates/pricing/constraints cannot
        # disappear merely because the planner chose a weaker semantic query.
        if len(chunks)<=max_evidence:
            for chunk in chunks:
                sid=str(chunk['id'])
                if sid not in selected:
                    selected[sid]={'id':len(selected)+1,'chunk_id':chunk['id'],'location':chunk['location'],
                                   'text':chunk['text'],'retrieved_for':'Full short-brief coverage'}
        return list(selected.values())
    finally:
        client.delete_collection(name)
