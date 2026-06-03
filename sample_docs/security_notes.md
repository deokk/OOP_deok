# Security Notes for Document Retrieval

Document retrieval systems can expose sensitive information if permissions are
not handled carefully. A local tool should make it clear which folder is being
indexed and which documents are used as evidence for an answer.

Prompt injection is another risk. A retrieved document may contain instructions
that try to control the answer generator. In a safer design, retrieved text is
treated as evidence data, not as commands to execute.

Citations and transparent retrieval logs help users audit the result. When the
system shows the file path, chunk number, and score for each retrieved passage,
the user can inspect whether the answer is actually supported by the documents.
