import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path


MODEL_DIR = Path(__file__).resolve().parent / "ml_models"
DEFAULT_MODEL_PATH = MODEL_DIR / "document_classifier.json"


TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_\-./]{1,}")
STOPWORDS = {
    "and", "are", "for", "from", "have", "into", "not", "the", "this",
    "that", "with", "your", "you", "was", "were", "will", "shall", "can",
    "may", "our", "their", "there", "here", "page", "date", "name",
}


def normalize_training_text(text):
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text, max_tokens=5000):
    tokens = []
    for token in TOKEN_RE.findall((text or "").lower()):
        token = token.strip("._-/")
        if len(token) < 2 or token in STOPWORDS:
            continue
        tokens.append(token)
        if len(tokens) >= max_tokens:
            break

    features = list(tokens)
    for left, right in zip(tokens, tokens[1:]):
        if len(features) >= max_tokens:
            break
        features.append(f"{left}__{right}")

    return features


class MultinomialTextClassifier:
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.labels = []
        self.label_doc_counts = Counter()
        self.label_token_counts = defaultdict(Counter)
        self.label_doc_feature_counts = defaultdict(Counter)
        self.label_total_tokens = Counter()
        self.token_doc_counts = Counter()
        self.vocabulary = set()
        self.total_docs = 0
        self.trained_at = None
        self.training_summary = {}

    def fit(self, examples):
        for text, label in examples:
            label = str(label).strip()
            if not label:
                continue

            tokens = tokenize(text)
            if not tokens:
                continue
            unique_tokens = set(tokens)

            self.total_docs += 1
            self.label_doc_counts[label] += 1
            self.label_token_counts[label].update(tokens)
            self.label_doc_feature_counts[label].update(unique_tokens)
            self.label_total_tokens[label] += len(tokens)
            self.vocabulary.update(tokens)
            self.token_doc_counts.update(unique_tokens)

        self.labels = sorted(self.label_doc_counts)
        if len(self.labels) < 2:
            raise ValueError("At least two labels with extractable text are required to train the classifier.")
        return self

    def _idf(self, token):
        return math.log((1 + self.total_docs) / (1 + self.token_doc_counts.get(token, 0))) + 1.0

    def _predict_by_centroid(self, tokens):
        if not self.label_doc_feature_counts or not self.token_doc_counts:
            return None

        doc_counts = Counter(tokens)
        doc_weights = {
            token: (1.0 + math.log(count)) * self._idf(token)
            for token, count in doc_counts.items()
            if token in self.vocabulary
        }
        if not doc_weights:
            return None

        doc_norm = math.sqrt(sum(weight * weight for weight in doc_weights.values())) or 1.0
        scores = {}

        for label in self.labels:
            label_docs = max(self.label_doc_counts[label], 1)
            feature_counts = self.label_doc_feature_counts[label]
            dot = 0.0
            label_norm_sq = 0.0

            for token, label_count in feature_counts.items():
                # How often this token appears across documents of this label,
                # weighted down if it appears in many labels/documents.
                weight = (label_count / label_docs) * self._idf(token)
                label_norm_sq += weight * weight
                if token in doc_weights:
                    dot += doc_weights[token] * weight

            label_norm = math.sqrt(label_norm_sq) or 1.0
            cosine = dot / (doc_norm * label_norm)
            prior = math.log((self.label_doc_counts[label] + 1) / (self.total_docs + len(self.labels)))
            scores[label] = cosine + 0.03 * prior

        if not scores:
            return None

        best_label = max(scores, key=scores.get)
        max_score = scores[best_label]
        exp_scores = {label: math.exp((score - max_score) * 8.0) for label, score in scores.items()}
        total = sum(exp_scores.values()) or 1.0
        confidence = exp_scores[best_label] / total
        ranked = sorted(
            ((label, exp_scores[label] / total) for label in self.labels),
            key=lambda item: item[1],
            reverse=True,
        )
        margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)

        return {
            "category": best_label,
            "confidence": round(confidence, 4),
            "margin": round(margin, 4),
            "alternatives": [
                {"category": label, "confidence": round(prob, 4)}
                for label, prob in ranked[:3]
            ],
        }

    def predict(self, text):
        if not self.labels:
            return None

        tokens = tokenize(text)
        if not tokens:
            return None

        centroid_result = self._predict_by_centroid(tokens)
        if centroid_result:
            return centroid_result

        vocab_size = max(len(self.vocabulary), 1)
        scores = {}

        for label in self.labels:
            prior = math.log((self.label_doc_counts[label] + self.alpha) / (self.total_docs + self.alpha * len(self.labels)))
            denom = self.label_total_tokens[label] + self.alpha * vocab_size
            score = prior
            counts = self.label_token_counts[label]

            for token in tokens:
                score += math.log((counts.get(token, 0) + self.alpha) / denom)

            scores[label] = score

        best_label = max(scores, key=scores.get)
        max_score = scores[best_label]
        exp_scores = {label: math.exp(score - max_score) for label, score in scores.items()}
        total = sum(exp_scores.values()) or 1.0
        confidence = exp_scores[best_label] / total

        ranked = sorted(
            ((label, exp_scores[label] / total) for label in self.labels),
            key=lambda item: item[1],
            reverse=True,
        )
        margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)

        return {
            "category": best_label,
            "confidence": round(confidence, 4),
            "margin": round(margin, 4),
            "alternatives": [
                {"category": label, "confidence": round(prob, 4)}
                for label, prob in ranked[:3]
            ],
        }

    def to_dict(self):
        return {
            "version": 1,
            "alpha": self.alpha,
            "labels": self.labels,
            "label_doc_counts": dict(self.label_doc_counts),
            "label_token_counts": {
                label: dict(counter)
                for label, counter in self.label_token_counts.items()
            },
            "label_doc_feature_counts": {
                label: dict(counter)
                for label, counter in self.label_doc_feature_counts.items()
            },
            "label_total_tokens": dict(self.label_total_tokens),
            "token_doc_counts": dict(self.token_doc_counts),
            "vocabulary": sorted(self.vocabulary),
            "total_docs": self.total_docs,
            "trained_at": self.trained_at,
            "training_summary": self.training_summary,
        }

    @classmethod
    def from_dict(cls, payload):
        model = cls(alpha=payload.get("alpha", 0.35))
        model.labels = list(payload.get("labels", []))
        model.label_doc_counts = Counter(payload.get("label_doc_counts", {}))
        model.label_token_counts = defaultdict(Counter)
        for label, counts in payload.get("label_token_counts", {}).items():
            model.label_token_counts[label] = Counter(counts)
        model.label_doc_feature_counts = defaultdict(Counter)
        for label, counts in payload.get("label_doc_feature_counts", {}).items():
            model.label_doc_feature_counts[label] = Counter(counts)
        model.label_total_tokens = Counter(payload.get("label_total_tokens", {}))
        model.token_doc_counts = Counter(payload.get("token_doc_counts", {}))
        model.vocabulary = set(payload.get("vocabulary", []))
        model.total_docs = int(payload.get("total_docs", 0))
        model.trained_at = payload.get("trained_at")
        model.training_summary = payload.get("training_summary", {})
        return model

    def save(self, path=DEFAULT_MODEL_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False)
        os.replace(tmp_path, path)

    @classmethod
    def load(cls, path=DEFAULT_MODEL_PATH):
        path = Path(path)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


_cached_model = None
_cached_mtime = None
# BUG-B05 FIX: Lock prevents two threads simultaneously loading the model from disk.
_model_lock = __import__("threading").Lock()


def load_model(path=DEFAULT_MODEL_PATH):
    global _cached_model, _cached_mtime
    path = Path(path)
    if not path.exists():
        with _model_lock:
            _cached_model = None
            _cached_mtime = None
        return None

    mtime = path.stat().st_mtime
    if _cached_model is not None and _cached_mtime == mtime:
        return _cached_model

    with _model_lock:
        # Double-checked locking: re-read after acquiring lock.
        if _cached_model is not None and _cached_mtime == mtime:
            return _cached_model
        _cached_model = MultinomialTextClassifier.load(path)
        _cached_mtime = mtime
    return _cached_model


def predict_document_category(text, threshold=0.62, path=DEFAULT_MODEL_PATH):
    model = load_model(path)
    if model is None:
        return None

    result = model.predict(normalize_training_text(text))
    if result is None:
        return None

    result["accepted"] = result["confidence"] >= threshold
    result["model_path"] = str(Path(path))
    return result
