"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import math

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None, min_evidence_score=2):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client
        # Minimum numeric score required to consider a snippet as evidence.
        # If the best snippet score is below this, the bot will refuse to answer.
        self.min_evidence_score = min_evidence_score

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        TODO (Phase 1):
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }

        Keep this simple: split on whitespace, lowercase tokens,
        ignore punctuation if needed.
        """
        index = {}
        for filename, text in documents:
            words = text.lower().split()
            for word in words:
                # Strip basic punctuation
                word = word.strip('.,!?;:()[]{}"\'-')
                if word:
                    if word not in index:
                        index[word] = []
                    if filename not in index[word]:
                        index[word].append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        TODO (Phase 1):
        Return a simple relevance score for how well the text matches the query.

        Suggested baseline:
        - Convert query into lowercase words
        - Count how many appear in the text
        - Return the count as the score
        """
        # Improved scoring: TF-IDF style with length normalization to penalize
        # generic matches. Uses the inverted index built in `build_index`
        # (which maps words -> filenames) to compute IDF over documents.

        punct = '.,!?;:()[]{}"\'"-'
        query_tokens = [w.strip(punct) for w in query.lower().split() if w.strip(punct)]
        if not query_tokens:
            return 0

        # Tokenize the section text
        section_tokens = [w.strip(punct) for w in text.lower().split() if w.strip(punct)]
        if not section_tokens:
            return 0

        section_token_counts = {}
        for t in section_tokens:
            section_token_counts[t] = section_token_counts.get(t, 0) + 1

        # Number of documents in the corpus (for IDF)
        n_docs = len(self.documents) if hasattr(self, 'documents') else 1

        score = 0.0
        matched_distinct = 0
        for token in set(query_tokens):
            if not token:
                continue
            tf = section_token_counts.get(token, 0)
            if tf <= 0:
                continue
            # Document frequency: number of documents containing the token
            df = len(self.index.get(token, [])) if hasattr(self, 'index') else 0
            # IDF smoothing
            idf = math.log((n_docs + 1) / (df + 1)) if n_docs > 0 else 0.0
            # accumulate TF * IDF
            score += tf * idf
            matched_distinct += 1

        if matched_distinct == 0:
            return 0

        # Length normalization: prefer compact sections with concentrated matches
        length_norm = 1.0 + len(section_tokens)
        normalized = score / length_norm

        # Scale to an integer score for compatibility with existing checks
        scaled = int(round(normalized * 100))
        return scaled

    def retrieve(self, query, top_k=3):
        """
        TODO (Phase 1):
        Use the index and scoring function to select top_k relevant document snippets.

        Return a list of (filename, text) sorted by score descending.
        """
        scored_sections = []

        for filename, text in self.documents:
            # Split text into sections by double newlines (paragraphs).
            # This keeps returned chunks smaller and more focused.
            sections = text.split('\n\n')

            for section in sections:
                if section.strip():  # Skip empty sections
                    score = self.score_document(query, section)
                    if score > 0:
                        # Store tuples as (score, filename, section)
                        scored_sections.append((score, filename, section))

        # Sort by score descending
        scored_sections.sort(key=lambda x: x[0], reverse=True)

        # Return top_k as (filename, section, score) tuples
        results = [(filename, section, score) for score, filename, section in scored_sections]
        return results[:top_k]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        # Retrieve scored snippets: list of (filename, section, score)
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        # Guardrail: require the top snippet to have enough evidence
        top_score = max(s[2] for s in snippets)
        if top_score < self.min_evidence_score:
            return "I do not know based on these docs."

        formatted = []
        for filename, section, score in snippets:
            formatted.append(f"[{filename}] (score: {score})\n{section}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        # Retrieve scored snippets: list of (filename, section, score)
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        # Guardrail: require the top snippet to have enough evidence
        top_score = max(s[2] for s in snippets)
        if top_score < self.min_evidence_score:
            return "I do not know based on these docs."

        # LLM expects (filename, text) pairs - strip scores before passing
        llm_snippets = [(fn, sec) for fn, sec, sc in snippets]
        return self.llm_client.answer_from_snippets(query, llm_snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
