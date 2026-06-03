# Object-Oriented Architecture for a Local RAG Tool

A local RAG tool can be designed with object-oriented programming by assigning
each responsibility to a separate class. A document loader reads files from disk.
A chunker decides how documents are split. An embedding or vector index converts
text into searchable numerical representations. A retriever returns the most
relevant chunks. An answer generator formats the final response.

Encapsulation is used when internal lists, vectors, and configuration values are
kept inside classes instead of being modified globally. Abstraction is used when
base classes define common methods such as load, split, search, or generate.

Inheritance allows concrete classes such as MarkdownTextLoader or
TfidfVectorIndex to extend abstract parent classes. Polymorphism allows the main
application to depend on a generic retriever or answer generator interface, so
the implementation can later be replaced with a different algorithm.
