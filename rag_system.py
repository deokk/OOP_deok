from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
import argparse
import math
import re


class Document:
    """A source file loaded from disk."""

    def __init__(self, document_id, path, title, text):
        self._document_id = document_id
        self._path = Path(path)
        self._title = title
        self._text = text

    @property
    def document_id(self):
        return self._document_id

    @property
    def path(self):
        return self._path

    @property
    def title(self):
        return self._title

    @property
    def text(self):
        return self._text


class Chunk:
    """A searchable passage created from a document."""

    def __init__(self, chunk_id, document, text, start_word, end_word):
        self._chunk_id = chunk_id
        self._document = document
        self._text = text
        self._start_word = start_word
        self._end_word = end_word

    @property
    def chunk_id(self):
        return self._chunk_id

    @property
    def document(self):
        return self._document

    @property
    def text(self):
        return self._text

    def source_label(self):
        return (
            f"{self._document.path} "
            f"(words {self._start_word}-{self._end_word}, chunk {self._chunk_id})"
        )


class DocumentLoader(ABC):
    """Abstract loader for source documents."""

    @abstractmethod
    def load(self, folder_path):
        pass


class MarkdownTextLoader(DocumentLoader):
    """Loads Markdown and text files from a folder."""

    def __init__(self, allowed_extensions=None):
        self._allowed_extensions = allowed_extensions or {".md", ".txt"}

    def load(self, folder_path):
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Document folder does not exist: {folder}")

        documents = []
        files = sorted(
            path for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in self._allowed_extensions
        )

        for index, path in enumerate(files, start=1):
            text = path.read_text(encoding="utf-8")
            title = self._extract_title(path, text)
            documents.append(Document(f"D{index}", path, title, text))

        return documents

    def _extract_title(self, path, text):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return path.stem.replace("_", " ").title()


class Chunker(ABC):
    """Abstract chunking strategy."""

    @abstractmethod
    def split(self, documents):
        pass


class ParagraphChunker(Chunker):
    """Splits documents into paragraph-based chunks."""

    def __init__(self, max_words=120):
        self._max_words = max_words

    def split(self, documents):
        chunks = []
        for document in documents:
            paragraphs = self._extract_paragraphs(document.text)
            current_words = []
            start_word = 1
            current_start_word = 1

            for paragraph in paragraphs:
                paragraph_words = paragraph.split()
                if not paragraph_words:
                    continue

                would_exceed_limit = (
                    current_words and
                    len(current_words) + len(paragraph_words) > self._max_words
                )
                if would_exceed_limit:
                    self._add_chunk(chunks, document, current_words, current_start_word)
                    current_start_word = start_word
                    current_words = []

                current_words.extend(paragraph_words)
                start_word += len(paragraph_words)

            if current_words:
                self._add_chunk(chunks, document, current_words, current_start_word)

        return chunks

    def _extract_paragraphs(self, text):
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        raw_paragraphs = re.split(r"\n\s*\n", text)
        return [re.sub(r"\s+", " ", item).strip() for item in raw_paragraphs]

    def _add_chunk(self, chunks, document, words, start_word):
        end_word = start_word + len(words) - 1
        chunk_id = f"{document.document_id}-C{len(chunks) + 1}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            document=document,
            text=" ".join(words),
            start_word=start_word,
            end_word=end_word
        ))


class TextProcessor:
    """Tokenizes English and Korean text for search."""

    def __init__(self):
        self._stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "can", "for",
            "from", "has", "have", "how", "in", "is", "it", "its", "of",
            "on", "or", "should", "that", "the", "then", "this", "to",
            "when", "which", "why", "with"
        }

    def tokenize(self, text):
        pattern = r"[a-zA-Z][a-zA-Z0-9_-]*|[\uac00-\ud7a3]+"
        words = re.findall(pattern, text.lower())
        tokens = []
        for word in words:
            if word in self._stop_words:
                continue

            normalized_word = self._normalize_token(word)
            tokens.append(normalized_word)

            if self._contains_korean(normalized_word):
                tokens.extend(self._character_ngrams(normalized_word))

        return tokens

    def _normalize_token(self, word):
        if len(word) > 5 and word.endswith("ies"):
            return word[:-3] + "y"
        if len(word) > 5 and word.endswith("ing"):
            return word[:-3]
        if len(word) > 4 and word.endswith("s"):
            return word[:-1]
        if re.search(r"[\uac00-\ud7a3]", word):
            suffixes = (
                "\uc73c\ub85c", "\uc5d0\uc11c", "\uc5d0\uac8c",
                "\uc774\ub77c\ub294", "\uc785\ub2c8\ub2e4", "\uc774\uba70",
                "\ud558\uace0", "\uc5d0\ub294", "\uc740", "\ub294",
                "\uc774", "\uac00", "\uc744", "\ub97c", "\uc5d0"
            )
            for suffix in suffixes:
                if len(word) > len(suffix) + 1 and word.endswith(suffix):
                    return word[:-len(suffix)]
        return word

    def _contains_korean(self, word):
        return re.search(r"[\uac00-\ud7a3]", word) is not None

    def _character_ngrams(self, word):
        ngrams = []
        for size in (2, 3):
            if len(word) < size:
                continue
            for index in range(0, len(word) - size + 1):
                ngrams.append(word[index:index + size])
        return ngrams


class QueryExpander:
    """Adds practical domain aliases before retrieval."""

    def __init__(self):
        self._aliases = {
            "oop": ["object", "oriented", "encapsulation", "abstraction", "polymorphism"],
            "rag": ["retrieval", "augmented", "generation", "context"],
            "algorithm": ["retriever", "index", "ranking", "implementation"],
            "algorithms": ["retriever", "index", "ranking", "implementation"],
            "citation": ["source", "evidence"],
            "secure": ["security", "permission", "sensitive"],
            "prompt": ["injection", "instruction", "malicious"]
        }

    def expand(self, query):
        pattern = r"[a-zA-Z][a-zA-Z0-9_-]*|[\uac00-\ud7a3]+"
        expanded_terms = []
        for token in re.findall(pattern, query.lower()):
            expanded_terms.extend(self._aliases.get(token, []))
        if not expanded_terms:
            return query
        return query + " " + " ".join(expanded_terms)


class SearchResult:
    """One ranked retrieval result."""

    def __init__(self, chunk, score):
        self._chunk = chunk
        self._score = score

    @property
    def chunk(self):
        return self._chunk

    @property
    def score(self):
        return self._score


class Retriever(ABC):
    """Abstract parent class for retrieval algorithms."""

    @abstractmethod
    def build(self, chunks):
        pass

    @abstractmethod
    def retrieve(self, query, top_k):
        pass


class KeywordRetriever(Retriever):
    """Ranks chunks by direct keyword overlap."""

    def __init__(self, text_processor, query_expander):
        self._text_processor = text_processor
        self._query_expander = query_expander
        self._chunks = []
        self._chunk_terms = []

    def build(self, chunks):
        self._chunks = list(chunks)
        self._chunk_terms = [
            Counter(self._text_processor.tokenize(chunk.text))
            for chunk in self._chunks
        ]

    def retrieve(self, query, top_k):
        expanded_query = self._query_expander.expand(query)
        query_terms = set(self._text_processor.tokenize(expanded_query))
        results = []

        for chunk, term_counts in zip(self._chunks, self._chunk_terms):
            matched_terms = query_terms & set(term_counts.keys())
            score = sum(term_counts[term] for term in matched_terms)
            if score > 0:
                normalized_score = score / max(len(term_counts), 1)
                results.append(SearchResult(chunk, normalized_score))

        results.sort(key=lambda result: result.score, reverse=True)
        return results[:top_k]


class BM25Retriever(Retriever):
    """Ranks chunks with the BM25 information retrieval algorithm."""

    def __init__(self, text_processor, query_expander, k1=1.5, b=0.75):
        self._text_processor = text_processor
        self._query_expander = query_expander
        self._k1 = k1
        self._b = b
        self._chunks = []
        self._term_frequencies = []
        self._document_frequency = Counter()
        self._average_length = 0

    def build(self, chunks):
        self._chunks = list(chunks)
        self._term_frequencies = []
        self._document_frequency = Counter()
        total_length = 0

        for chunk in self._chunks:
            tokens = self._text_processor.tokenize(chunk.text)
            term_frequency = Counter(tokens)
            self._term_frequencies.append(term_frequency)
            self._document_frequency.update(set(tokens))
            total_length += len(tokens)

        self._average_length = total_length / max(len(self._chunks), 1)

    def retrieve(self, query, top_k):
        expanded_query = self._query_expander.expand(query)
        query_terms = self._text_processor.tokenize(expanded_query)
        results = []

        for chunk, term_frequency in zip(self._chunks, self._term_frequencies):
            score = self._score_chunk(query_terms, term_frequency)
            if score > 0:
                results.append(SearchResult(chunk, score))

        results.sort(key=lambda result: result.score, reverse=True)
        return results[:top_k]

    def _score_chunk(self, query_terms, term_frequency):
        score = 0.0
        chunk_length = sum(term_frequency.values())
        total_chunks = max(len(self._chunks), 1)

        for term in query_terms:
            frequency = term_frequency.get(term, 0)
            if frequency == 0:
                continue

            docs_with_term = self._document_frequency.get(term, 0)
            idf = math.log(1 + (total_chunks - docs_with_term + 0.5) / (docs_with_term + 0.5))
            denominator = frequency + self._k1 * (
                1 - self._b + self._b * chunk_length / max(self._average_length, 1)
            )
            score += idf * (frequency * (self._k1 + 1)) / denominator

        return score


class AnswerGenerator(ABC):
    """Abstract answer generator."""

    @abstractmethod
    def generate(self, query, results):
        pass


class ExtractiveAnswerGenerator(AnswerGenerator):
    """Builds an answer by selecting evidence sentences from retrieved chunks."""

    def __init__(self, text_processor):
        self._text_processor = text_processor

    def generate(self, query, results):
        if not results:
            return (
                "I could not find enough evidence in the indexed documents.\n"
                "Try adding more documents or using a more specific query."
            )

        query_terms = set(self._text_processor.tokenize(query))
        selected_sentences = []

        for result in results:
            best_sentence = self._select_best_sentence(result.chunk.text, query_terms)
            selected_sentences.append((best_sentence, result))

        lines = ["Answer:"]
        for sentence, result in selected_sentences:
            lines.append(f"- {sentence} [{result.chunk.chunk_id}]")

        lines.append("")
        lines.append("Sources:")
        for rank, result in enumerate(results, start=1):
            lines.append(
                f"{rank}. [{result.chunk.chunk_id}] score={result.score:.3f} "
                f"{result.chunk.source_label()}"
            )

        return "\n".join(lines)

    def _select_best_sentence(self, text, query_terms):
        sentences = re.split(r"(?<=[.!?])\s+", text)
        best_sentence = sentences[0] if sentences else text
        best_score = -1

        for sentence in sentences:
            sentence_terms = set(self._text_processor.tokenize(sentence))
            score = len(query_terms & sentence_terms)
            is_better_tie = (
                score == best_score and
                len(sentence.split()) < len(best_sentence.split())
            )
            if score > best_score or is_better_tie:
                best_sentence = sentence
                best_score = score

        return best_sentence.strip()


class LocalRAGApplication:
    """High-level application object that wires the RAG pipeline together."""

    def __init__(self, loader, chunker, retriever, answer_generator):
        self._loader = loader
        self._chunker = chunker
        self._retriever = retriever
        self._answer_generator = answer_generator
        self._documents = []
        self._chunks = []

    def index_folder(self, folder_path):
        self._documents = self._loader.load(folder_path)
        self._chunks = self._chunker.split(self._documents)
        self._retriever.build(self._chunks)

    def ask(self, query, top_k=4):
        results = self._retriever.retrieve(query, top_k)
        return self._answer_generator.generate(query, results)

    def status(self):
        return (
            f"Indexed {len(self._documents)} documents and "
            f"{len(self._chunks)} chunks."
        )


def create_retriever(name, text_processor, query_expander):
    retrievers = {
        "keyword": KeywordRetriever,
        "bm25": BM25Retriever
    }
    if name not in retrievers:
        choices = ", ".join(sorted(retrievers.keys()))
        raise ValueError(f"Unknown retriever '{name}'. Choose one of: {choices}")
    return retrievers[name](text_processor, query_expander)


def build_application(chunk_size=120, retriever_name="bm25"):
    text_processor = TextProcessor()
    query_expander = QueryExpander()
    loader = MarkdownTextLoader()
    chunker = ParagraphChunker(max_words=chunk_size)
    retriever = create_retriever(retriever_name, text_processor, query_expander)
    answer_generator = ExtractiveAnswerGenerator(text_processor)
    return LocalRAGApplication(loader, chunker, retriever, answer_generator)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Local document RAG search tool with interchangeable retrievers."
    )
    parser.add_argument(
        "--docs",
        default="sample_docs",
        help="Folder containing .md or .txt documents to index."
    )
    parser.add_argument(
        "--query",
        help="Question to ask. If omitted, interactive mode starts."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of evidence chunks to retrieve."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=120,
        help="Maximum number of words per paragraph-based chunk."
    )
    parser.add_argument(
        "--retriever",
        choices=["keyword", "bm25"],
        default="bm25",
        help="Retrieval algorithm to use."
    )
    return parser.parse_args()


def run_interactive(application, top_k, retriever_name):
    print(f"Interactive mode using '{retriever_name}' retriever. Type 'exit' to quit.")
    while True:
        query = input("\nQuestion> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue
        print(application.ask(query, top_k=top_k))


def main():
    args = parse_args()
    application = build_application(
        chunk_size=args.chunk_size,
        retriever_name=args.retriever
    )
    application.index_folder(args.docs)
    print(application.status())
    print(f"Retriever: {args.retriever}")

    if args.query:
        print(application.ask(args.query, top_k=args.top_k))
    else:
        run_interactive(application, top_k=args.top_k, retriever_name=args.retriever)


if __name__ == "__main__":
    main()
