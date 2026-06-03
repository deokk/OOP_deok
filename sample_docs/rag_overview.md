# Retrieval-Augmented Generation Overview

Retrieval-Augmented Generation, usually called RAG, is a pattern for answering
questions using external documents. A RAG system first searches a document
collection, selects passages that are likely to contain useful evidence, and
then generates an answer grounded in those passages.

RAG is useful when the answer should depend on private, recent, or domain-specific
documents. Instead of relying only on a language model's stored knowledge, the
system provides retrieved context at question time.

A practical RAG pipeline usually contains a document loader, a chunker, an
index, a retriever, and an answer generator. The document loader reads source
files, the chunker splits them into smaller passages, the index stores searchable
representations, the retriever ranks passages for a query, and the answer
generator produces a response with citations.
