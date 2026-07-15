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
        punct = '.,!?;:()[]{}"\'"-'
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'to', 'of', 'in', 'on', 'for', 'with', 'at', 'by', 'from', 'as',
            'and', 'or', 'if', 'but', 'not', 'this', 'that', 'these', 'those',
            'their', 'there', 'here', 'when', 'where', 'who', 'what', 'why',
            'how', 'which', 'does', 'do', 'did', 'have', 'has', 'had', 'can',
            'could', 'should', 'would', 'will', 'about', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'under', 'over',
            'then', 'than', 'so', 'because', 'also'
        }

        query_tokens = [
            token for token in
            (w.strip(punct) for w in query.lower().split())
            if token and token not in stopwords and len(token) > 1
        ]
        if not query_tokens:
            return 0

        text_tokens = [
            token for token in
            (w.strip(punct) for w in text.lower().split())
            if token
        ]
        if not text_tokens:
            return 0

        score = 0
        for token in query_tokens:
            score += text_tokens.count(token)
        return score

    def retrieve(self, query, top_k=3):
        """
        TODO (Phase 1):
        Use the index and scoring function to select top_k relevant document snippets.

        Return a list of (filename, text) sorted by score descending.
        """
        scored_sections = []

        for filename, text in self.documents:
            # Split text into sections by double newlines (paragraphs).
            sections = [section.strip() for section in text.split('\n\n') if section.strip()]

            for index, section in enumerate(sections):
                # Create a small context window around the matching paragraph.
                combined = section
                if index + 1 < len(sections):
                    combined = f"{section}\n\n{sections[index + 1]}"

                score = self.score_document(query, combined)
                if score > 0:
                    scored_sections.append((score, filename, combined))

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
            return "I can't help you. I do not know based on these docs."

        # Guardrail: require the top snippet to have enough evidence
        top_score = max(s[2] for s in snippets)
        if top_score < self.min_evidence_score:
            return "I can't help you. I do not know based on these docs."

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
            return "I can't help you. I do not know based on these docs."

        # Guardrail: require the top snippet to have enough evidence
        top_score = max(s[2] for s in snippets)
        if top_score < self.min_evidence_score:
            return "I can't help you. I do not know based on these docs."

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
