# DocuBot Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
Describe the overall goal in 2 to 3 sentences.

> _Your answer here._


DocuBot allows users to ask questions about a document and quickly find reliable answers. This uses 3 modes to find the relevant information for the user which is LLM generation, retrieval only and RAG. The user has the option to choose which mode they want.

**What inputs does DocuBot take?**  
For example: user question, docs in folder, environment variables.

> _Your answer here._

DocuBot takes the user question as the input and also takes documents from the docs folder to find relevant information. This also uses an environment variable which is the API Key to search any outside sources.

**What outputs does DocuBot produce?**

> _Your answer here._

This provides a detailed answer to the user's question based on the documents it used and the mode the user chose. Depending on the mode the output may be a direct LLM-generated answer, a list of relevant retrieved documents and RAG that combines document retrieval with an LLM response.

---

## 2. Retrieval Design

**How does your retrieval system work?**  
Describe your choices for indexing and scoring.

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

> _Your answer here._

My retrieval systems loads all the .md files from the docs folder and turns them into an index. The index maps each word to the documents that it appears in. With scoring, the system compares the word with each document and if words appear a few times in a document, they are treated as more important.

**What tradeoffs did you make?**  
For example: speed vs precision, simplicity vs accuracy.

> _Your answer here._

One tradeoff I did was doing simplicity vs accuracy where I simply used a index and word count scoring instead of using a more advanced search.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**  
Briefly describe how each mode behaves.

- Naive LLM mode:

The model uses
- Retrieval only mode:
- RAG mode:

> _Your answer here._

- Naive LLM mode:

The model uses the LLM to generate an answer but doesn't do retrieval from the documents. This may lead to less accurate answers if documents are too large or the model can't find the right information.

- Retrieval only mode:

DocuBot uses the retrieval system to search documents and return the most relevant information. This would show the exact sections of the document that matches the user's question. 

- RAG mode:

DocuBot uses the retrieval system to search documents like Retrieval only but this also uses the LLM to get better evidence leading to less incorrect answers.

**What instructions do you give the LLM to keep it grounded?**  
Summarize the rules from your prompt. For example: only use snippets, say "I do not know" when needed, cite files.

> _Your answer here._

I instruct the LLM to only use retrieved documents so that the LLM doesn't go off topic and make up an answer. The LLM would cite the source files it used so the user would know where the answer came from.
---

## 4. Experiments and Comparisons

Run the **same set of queries** in all three modes. Fill in the table with short notes.

You can reuse or adapt the queries from `dataset.py`.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Example: Where is the auth token generated? | Harmful | Helpful | Helpful | Retrieval Only was the only mode that answered the user's question but RAG explained that due to API error it couldn't answer the question. |
| Example: How do I connect to the database? | Harmful | Helpful | Helpful | Retrieval Only was the only mode that answered the user's question but RAG explained that due to API error it couldn't answer the question. |
| Example: Which endpoint lists all users? | Harmful | Helpful | Helpful | Retrieval Only was the only mode that answered the user's question but RAG explained that due to API error it couldn't answer the question. |
| Example: How does a client refresh an access token? | Harmful | Helpful | Helpful | Retrieval Only was the only mode that answered the user's question but RAG explained that due to API error it couldn't answer the question. |

**What patterns did you notice?**  

- When does naive LLM look impressive but untrustworthy?  
- When is retrieval only clearly better?  
- When is RAG clearly better than both?

> _Your answer here._

Naive LLM mode can look impressive because it gives a clear and polished answer, but it is not always trustworthy because it may guess or include details that are not supported by the documents. Retrieval-only mode is better when I need exact evidence because it shows the matching snippets and filenames directly from the docs. RAG is the strongest overall because it combines both approaches: it first finds the most relevant snippets, then uses the LLM to create a clear answer based only on that evidence.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**  
For each one, say:

- What was the question?  
- What did the system do?  
- What should have happened instead?

> _Failure case 1 here._

When I asked the qustion "Where is the auth token generated?" when I used the LLM generation, it was unable to generate an answer. The system is supposed to use a model that uses outside sources that help answer my question.

> _Failure case 2 here._

When I asked "How do I connect to the database?" for retrieval only this just return important text from the document files and instead of returning a simple clear message to answer the user's question. 

**When should DocuBot say “I do not know based on the docs I have”?**  
Give at least two specific situations.

> _Your answer here._

DocuBot should say this when this doesn't have any evidence to answer the question. For example if the user asks about a payment process for a meal, if none of the documents mention payment, DocuBot should be honest and not guess. Another situation is if the  user asks about personal information outside of the doucments like someones SSN or company policies. 

**What guardrails did you implement?**  
Examples: refusal rules, thresholds, limits on snippets, safe defaults.

> _Your answer here._

I implemented several guardrails to keep DocuBot from giving unsupported answers. First, I used a minimum evidence score, so if the best retrieved snippet does not meet the required score, DocuBot can refuse to answer instead of guessing. I also limited retrieval to the top few snippets, such as the top 3, so the LLM only receives the most relevant evidence instead of too much unrelated text.

---

## 6. Limitations and Future Improvements

**Current limitations**  
List at least three limitations of your DocuBot system.

1. _Limitation 1_ 

One limitation is that DocuBot depends heavily on exact word matches. If the user asks a question using different wording than the documents, the retrieval system may miss the correct answer even if the information exists.

2. _Limitation 2_

A second limitation is that the system only knows about files inside the docs/ folder. If the answer is in another file, database, website, or source outside that folder, DocuBot cannot answer it correctly.

3. _Limitation 3_

A third limitation is that the retrieval and scoring system is simple. Even with TF-IDF style scoring, it may return snippets that contain matching words but do not actually answer the question. This means the system can sometimes retrieve weak or unrelated evidence.

**Future improvements**  
List two or three changes that would most improve reliability or usefulness.

1. _Improvement 1_

One future improvement would be to use embeddings instead of only keyword-based retrieval. This would help DocuBot understand similar meanings even when the user’s question uses different words than the documents.

2. _Improvement 2_

Another improvement would be to add better source citations, such as showing the exact filename and section where the answer came from.

3. _Improvement 3_

A third improvement would be to create a larger test set of questions and expected answers, so the system can be evaluated more reliably across different types of documentation questions.

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**  
Think about wrong answers, missing information, or over trusting the LLM.

> _Your answer here._

DocuBot could cause real world harm if users over-trust its answers without checking the original documents. For example, if it gives a wrong answer about authentication, database setup, or API endpoints, a developer might build something incorrectly or create a security issue. It could also miss important information if the answer is not in the retrieved snippets, which may cause users to think something does not exist when it actually does. Another risk is that the LLM might sound confident even when the documents do not support the answer, so DocuBot should clearly say when it does not know and should cite the files it used.

**What instructions would you give real developers who want to use DocuBot safely?**  
Write 2 to 4 short bullet points.

- _Guideline 1_

Developers should treat DocuBot’s answers as a starting point, not a final source of truth, and should always verify important answers against the original documents.

- _Guideline 2_

Developers should keep the documentation folder updated so DocuBot does not answer using missing or outdated information.

- _Guideline 3 (optional)_

---
