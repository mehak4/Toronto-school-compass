"""Local PDF/DOCX ingestion with source locations and explicit extraction warnings."""
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import unicodedata


@dataclass
class Document:
    name: str
    chunks: list[dict]
    warnings: list[str]

    def to_dict(self):
        return asdict(self)


def clean(text):
    text = unicodedata.normalize('NFKC', text).replace('\x00', '')
    return '\n'.join(re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines() if line.strip())


def load_document(path, chunk_chars=6000):
    path = Path(path)
    if path.suffix.lower() not in {'.pdf', '.docx'}:
        raise ValueError('Supported files: .pdf and .docx')
    if not 500 <= chunk_chars <= 20000:
        raise ValueError('chunk_chars must be between 500 and 20000')
    if not path.is_file() or path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Input must be an existing file of at most 25 MB')
    blocks, warnings = [], []
    try:
        if path.suffix.lower() == '.docx':
            from docx import Document as WordDocument
            from docx.table import Table
            doc = WordDocument(path)
            for i, item in enumerate(doc.iter_inner_content(), 1):
                if isinstance(item, Table):
                    text = '\n'.join(' | '.join(clean(c.text) for c in row.cells) for row in item.rows)
                else:
                    text = item.text
                blocks.append((f'body block {i}', clean(text)))
            warnings.append('DOCX locations are body blocks, not rendered page numbers; headers/footers are excluded. Text boxes and tracked changes may be omitted.')
        else:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = []
                edges = Counter()
                for page in pdf.pages:
                    text = clean(page.extract_text() or '')
                    lines = text.splitlines()
                    margins = page.crop((0, 0, page.width, page.height * .07)).extract_text() or ''
                    margins += '\n' + (page.crop((0, page.height * .93, page.width, page.height)).extract_text() or '')
                    edge_lines = set(clean(margins).splitlines())
                    edges.update(edge_lines)
                    pages.append((page.page_number, lines, page.extract_tables(), edge_lines))
                repeated = {s for s,n in edges.items() if len(pages) >= 2 and n >= max(2, len(pages)*.6)}
                for number, lines, tables, edge_lines in pages:
                    body = [s for s in lines if not (s in edge_lines and (s in repeated or re.fullmatch(r'(?:Page\s+)?\d+(?:\s+of\s+\d+)?',s,re.I)))]
                    text = '\n'.join(body)
                    if not text:
                        warnings.append(f'Page {number}: no readable body text; OCR may be needed.')
                    for table in tables:
                        text += '\n[Extracted table]\n' + '\n'.join(' | '.join(clean(c or '') for c in row) for row in table)
                    blocks.append((f'page {number}', clean(text)))
                if repeated:
                    warnings.append('Repeated PDF margin text removed heuristically; inspect the extracted document for omissions.')
                warnings.append('PDF tables are best effort and may duplicate text; scanned pages require external OCR.')
    except ImportError as exc:
        raise ValueError('Install document_agent/requirements.txt first') from exc
    except Exception as exc:
        raise ValueError('Unable to read document; it may be corrupt, encrypted or unsupported') from exc
    chunks = []
    for location, text in blocks:
        while text:
            end = min(len(text), chunk_chars)
            if end < len(text):
                boundary = text.rfind(' ', 0, end)
                if boundary > chunk_chars//2:
                    end = boundary
            chunks.append({'id':len(chunks)+1, 'location':location, 'text':text[:end]})
            text = text[end:].lstrip()
    if not chunks:
        raise ValueError('No readable text found. For scanned PDFs, run OCR first.')
    return Document(path.name, chunks, warnings)
