# OOP_deok
Object-Oriented Programming Project Assignment 2

## 프로젝트 개요

이 프로젝트는 로컬 폴더에 있는 Markdown/Text 문서를 색인하고, 사용자의 질문과 관련 있는 문서 조각을 찾아 근거 문장과 출처를 함께 출력하는 간단한 RAG(Retrieval-Augmented Generation) 시스템입니다.

외부 API나 데이터베이스 없이 Python 표준 라이브러리만 사용하며, 객체 지향 설계를 통해 문서 로딩, 청킹, 검색 알고리즘, 답변 생성을 각각 독립적인 클래스로 분리했습니다.

## 실행 방법

기본 샘플 문서를 색인한 뒤 대화형 모드로 실행합니다.

```bash
python rag_system.py
```

질문을 한 번만 실행하려면 `--query` 옵션을 사용합니다.

```bash
python rag_system.py --query "What is RAG?"
```

검색 알고리즘, 검색 결과 개수, 청크 크기도 옵션으로 바꿀 수 있습니다.

```bash
python rag_system.py --retriever keyword --top-k 3 --chunk-size 80
```

## 주요 옵션

- `--docs`: 색인할 문서 폴더 경로입니다. 기본값은 `sample_docs`입니다.
- `--query`: 실행할 질문입니다. 생략하면 대화형 모드가 시작됩니다.
- `--top-k`: 검색해서 답변에 사용할 문서 조각 개수입니다. 기본값은 `4`입니다.
- `--chunk-size`: 하나의 청크에 들어갈 최대 단어 수입니다. 기본값은 `120`입니다.
- `--retriever`: 검색 알고리즘을 선택합니다. `bm25` 또는 `keyword`를 사용할 수 있습니다.

## 코드 구조

전체 코드는 `rag_system.py`에 들어 있으며, 다음 순서로 동작합니다.

1. `MarkdownTextLoader`가 문서 폴더에서 `.md`, `.txt` 파일을 읽습니다.
2. `ParagraphChunker`가 문서를 문단 기준으로 나누고, 지정된 단어 수를 넘지 않도록 청크를 만듭니다.
3. `TextProcessor`가 영어와 한국어 텍스트를 검색용 토큰으로 변환합니다.
4. `QueryExpander`가 `rag`, `oop`, `prompt` 같은 주요 단어에 관련 검색어를 추가합니다.
5. `KeywordRetriever` 또는 `BM25Retriever`가 질문과 관련 있는 청크를 점수화해 정렬합니다.
6. `ExtractiveAnswerGenerator`가 검색된 청크에서 질문과 가장 잘 맞는 문장을 뽑아 답변과 출처를 출력합니다.

## 주요 클래스 설명

### 데이터 모델

- `Document`: 디스크에서 읽은 원본 문서를 표현합니다. 문서 ID, 경로, 제목, 본문을 가집니다.
- `Chunk`: 검색 단위가 되는 문서 조각입니다. 어떤 문서에서 왔는지와 단어 범위 정보를 함께 저장합니다.
- `SearchResult`: 검색된 청크와 점수를 묶어 표현합니다.

### 문서 로딩과 청킹

- `DocumentLoader`: 문서 로더가 따라야 하는 추상 클래스입니다.
- `MarkdownTextLoader`: 폴더 안의 Markdown/Text 파일을 읽어 `Document` 객체로 변환합니다. Markdown의 첫 번째 `# 제목`을 문서 제목으로 사용하고, 없으면 파일명을 제목으로 사용합니다.
- `Chunker`: 청킹 전략을 정의하는 추상 클래스입니다.
- `ParagraphChunker`: 문서를 문단 기준으로 분리한 뒤, 최대 단어 수에 맞게 여러 문단을 하나의 청크로 묶습니다.

### 텍스트 처리

- `TextProcessor`: 검색에 사용할 토큰을 생성합니다. 영어 불용어를 제거하고, 간단한 영어 어미 정규화와 한국어 조사 제거를 수행합니다. 한국어 검색 성능을 보완하기 위해 2글자, 3글자 n-gram도 추가합니다.
- `QueryExpander`: 자주 쓰는 도메인 용어에 관련 단어를 추가합니다. 예를 들어 `rag`는 `retrieval`, `augmented`, `generation`, `context` 같은 단어로 확장됩니다.

### 검색 알고리즘

- `Retriever`: 검색 알고리즘이 구현해야 하는 추상 클래스입니다. `build()`로 색인을 만들고, `retrieve()`로 검색합니다.
- `KeywordRetriever`: 질문 토큰과 청크 토큰의 직접 겹침 정도를 기준으로 점수를 계산합니다. 단순하지만 동작을 이해하기 쉽습니다.
- `BM25Retriever`: 정보 검색에서 많이 쓰이는 BM25 알고리즘으로 청크를 점수화합니다. 단어 빈도, 문서 빈도, 청크 길이를 함께 고려하기 때문에 기본 검색기로 사용됩니다.

### 답변 생성과 애플리케이션 연결

- `AnswerGenerator`: 답변 생성기가 따라야 하는 추상 클래스입니다.
- `ExtractiveAnswerGenerator`: 생성형 AI처럼 새 문장을 만드는 대신, 검색된 청크 안에서 질문과 가장 관련 있는 문장을 선택해 답변으로 보여줍니다. 각 답변에는 청크 ID와 출처가 함께 표시됩니다.
- `LocalRAGApplication`: 로더, 청커, 검색기, 답변 생성기를 하나로 연결하는 상위 애플리케이션 클래스입니다. `index_folder()`로 문서를 색인하고, `ask()`로 질문에 답합니다.

## 객체 지향 설계 포인트

- 추상 클래스(`DocumentLoader`, `Chunker`, `Retriever`, `AnswerGenerator`)를 사용해 역할별 인터페이스를 분리했습니다.
- 검색 알고리즘은 `Retriever` 인터페이스를 따르기 때문에 `keyword`와 `bm25`를 같은 방식으로 교체할 수 있습니다.
- `LocalRAGApplication`은 구체적인 검색 알고리즘의 내부 구현을 알 필요 없이 `retrieve()` 결과만 사용합니다.
- 문서 로딩, 텍스트 처리, 검색, 답변 생성 책임이 각각 다른 클래스로 분리되어 있어 기능 확장이 쉽습니다.

## 확장 아이디어

- PDF나 Word 문서를 읽는 새로운 `DocumentLoader` 구현 추가
- 문장 단위 또는 고정 길이 기반의 새로운 `Chunker` 구현 추가
- TF-IDF, 벡터 검색 등 새로운 `Retriever` 구현 추가
- 실제 LLM API와 연결하는 새로운 `AnswerGenerator` 구현 추가
- 검색 결과를 파일로 저장하거나 웹 UI에서 보여주는 기능 추가
