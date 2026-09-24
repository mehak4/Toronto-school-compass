"""Allowlisted document actions; no model-controlled filesystem or shell access."""
import re

SCHEMA = {'type':'function','function':{'name':'document_action',
 'description':'Read/search the document, record supported action items or requirements, or finish after reviewing every chunk.',
 'parameters':{'type':'object','properties':{
  'action':{'type':'string','enum':['read_chunk','search_document','record_actions','finish']},
  'reason':{'type':'string','description':'Short operational purpose, not hidden reasoning.'},
  'chunk_id':{'type':'integer','description':'For read_chunk, use a valid 1-based chunk number. Otherwise use 0.'}, 'query':{'type':'string','description':'Search text for search_document, otherwise empty string.'},
  'items':{'type':'array','items':{'type':'object','properties':{
    'chunk_id':{'type':'integer'},'quote':{'type':'string'},
    'owner':{'type':['string','null']},'due_date':{'type':['string','null']}},
    'required':['chunk_id','quote','owner','due_date'],'additionalProperties':False}}},
 'required':['action','reason','chunk_id','query','items'],'additionalProperties':False}}}


class DocumentTools:
    def __init__(self, document):
        self.document = document
        self.read = set()
        self.items = []
        self.finished = False

    def execute(self, args):
        if not isinstance(args,dict) or not isinstance(args.get('reason'),str) or not args['reason'].strip():
            raise ValueError('Provide an action and a short reason')
        action = args.get('action')
        if action == 'read_chunk':
            i = args.get('chunk_id')
            if type(i) is not int or not 1 <= i <= len(self.document.chunks):
                raise ValueError('Invalid chunk_id')
            self.read.add(i)
            return self.document.chunks[i-1]
        if action == 'search_document':
            query = args.get('query')
            if not isinstance(query,str) or not query.strip():
                raise ValueError('Provide a nonempty query')
            terms = set(re.findall(r'\w+',query.lower()))
            ranked = sorted(self.document.chunks,key=lambda c:len(terms & set(re.findall(r'\w+',c['text'].lower()))),reverse=True)
            matches = [c for c in ranked if terms & set(re.findall(r'\w+',c['text'].lower()))][:3]
            self.read.update(c['id'] for c in matches)
            return {'matches':matches}
        if action == 'record_actions':
            items = args.get('items')
            if not isinstance(items,list) or not 1 <= len(items) <= 30:
                raise ValueError('Provide 1–30 items')
            validated = []
            for item in items:
                if not isinstance(item,dict) or set(item) != {'chunk_id','quote','owner','due_date'}:
                    raise ValueError('Each item needs chunk_id, quote, owner and due_date')
                i, quote = item['chunk_id'], item['quote']
                if type(i) is not int or i not in self.read:
                    raise ValueError('Read the cited chunk first')
                if not isinstance(quote,str) or not quote.strip() or quote not in self.document.chunks[i-1]['text']:
                    raise ValueError('Quote must be an exact nonempty excerpt of the cited chunk')
                for field in ['owner','due_date']:
                    value = item[field]
                    if value is not None and (not isinstance(value,str) or not value.strip() or value not in quote):
                        raise ValueError(f'{field} must be null or verbatim text inside the quote')
                validated.append({**item,'location':self.document.chunks[i-1]['location']})
            for item in validated:
                if not any(old['quote']==item['quote'] and old['chunk_id']==item['chunk_id'] for old in self.items):
                    self.items.append(item)
            return {'saved_items':len(self.items)}
        if action == 'finish':
            missing = [c['id'] for c in self.document.chunks if c['id'] not in self.read]
            if missing:
                raise ValueError(f'Review all chunks before finishing; unread: {missing[:20]}')
            self.finished = True
            return {'complete':True,'saved_items':len(self.items)}
        raise ValueError('Unknown action')
