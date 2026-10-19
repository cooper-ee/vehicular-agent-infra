"""Local retrieval: Chinese bigram/Latin-token TF-IDF, optional model embeddings."""
from collections import Counter
from pathlib import Path
import math
import re
import hashlib
import numpy as np


def tokens(text):
    words = re.findall(r'[a-z0-9_]+', text.lower())
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        words.extend(run[i:i + 2] for i in range(max(1, len(run) - 1)))
    return words


class Retriever:
    def __init__(self, folder, embedding_model='', chunk_size=400, overlap=60):
        if not 0 <= overlap < chunk_size:
            raise ValueError('overlap must be smaller than chunk_size')
        self.chunks = []
        for path in sorted(Path(folder).glob('*.md')):
            text = path.read_text(encoding='utf-8')
            for offset in range(0, len(text), chunk_size - overlap):
                self.chunks.append({'source': path.name, 'offset': offset, 'text': text[offset:offset + chunk_size]})
        self.counts = [Counter(tokens(x['text'])) for x in self.chunks]
        self.revision = hashlib.sha256((embedding_model + repr(self.chunks)).encode('utf-8')).hexdigest()
        doc_freq = Counter(w for count in self.counts for w in count)
        self.idf = {w: math.log((1 + len(self.chunks)) / (1 + n)) + 1 for w, n in doc_freq.items()}
        self.model = None
        if embedding_model:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(embedding_model)
        self.vectors = self.model.encode([x['text'] for x in self.chunks], normalize_embeddings=True) if self.model and self.chunks else None

    def search(self, query, k=3):
        if not self.chunks:
            return []
        if self.model:
            vector = self.model.encode([query], normalize_embeddings=True)[0]
            scores = self.vectors @ vector
        else:
            q = {w: n * self.idf.get(w, 0.0) for w, n in Counter(tokens(query)).items()}
            qnorm = math.sqrt(sum(v * v for v in q.values())) or 1.0
            scores = []
            for count in self.counts:
                norm = math.sqrt(sum((n * self.idf[w]) ** 2 for w, n in count.items())) or 1.0
                scores.append(sum(value * count.get(w, 0) * self.idf.get(w, 0) for w, value in q.items()) / (norm * qnorm))
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))[:k]
        return [{**self.chunks[i], 'score': round(float(scores[i]), 6)} for i in order if scores[i] > 0]
