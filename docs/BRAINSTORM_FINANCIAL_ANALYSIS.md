# Brainstorming: Innovative Financial Analysis Adjudication
**Objective:** Replace hardcoded keywords/heuristics in "Related SEC Findings" with dynamic, financially sensitive signals.

## Framework: Think-Pause-Rethink

### 1. Mental Model: Inversion (The "Diff" Engine)
**Think:** "What are the key words in this filing?"
**Rethink:** "What *changed* in this filing compared to the last one?"
**Concept:** Instead of scoring the static text, score the **delta**.
-   **Implementation:**
    -   **Risk Factor Drift:** Calculate Cosine Similarity between the "Risk Factors" (Item 1A) of the current 10-K/Q and the previous one.
    -   **Signal:** Low similarity = High Relevance. It means the company is rewriting its risks (e.g., adding "AI regulation" or "Supply chain disruption").
    -   **Adjudication:** "Relevance Score" boosts if `similarity < 0.9`.

### 2. Mental Model: The Map is Not the Territory (Market-Derived Relevance)
**Think:** "Is this 8-K important based on its form type?"
**Rethink:** "Did the market *care* about this 8-K?"
**Concept:** Use **Price Velocity** as the ground truth for relevance, not the text.
-   **Implementation:**
    -   **Volatility Intersection:** Calculate the standard deviation of price returns in the 30 minutes *after* the filing timestamp.
    -   **Signal:** If `Post-Filing Volatility > 3x Average Volatility`, the filing is **Critical**, regardless of what it says.
    -   **Adjudication:** Override any text-based score if market reaction is violent. Label: "Market Mover".

### 3. Mental Model: Signal vs. Noise (Linguistic Entropy)
**Think:** "Does it contain the word 'lawsuit'?"
**Rethink:** "Is the language unusually complex or evasive?"
**Concept:** **Obfuscation Detection**.
-   **Implementation:**
    -   **Gunning-Fog Index:** Measure the readability complexity.
    -   **Hedge Word Density:** Count frequency of "may", "could", "might", "approximately".
    -   **Signal:** A sudden spike in complexity or hedge words often hides bad news (e.g., trying to bury a missed earnings target in complex prose).
    -   **Adjudication:** "High Complexity Alert" – likely hiding negative nuance.

### 4. Mental Model: Second-Order Thinking (The "Peer" Effect)
**Think:** "How does this affect AAPL?"
**Rethink:** "How does this compare to MSFT's filing yesterday?"
**Concept:** **Sector Benchmarking**.
-   **Implementation:**
    -   **Thematic Divergence:** If MSFT, GOOGL, and AMZN all mention "AI CapEx" in their 10-Qs, but AAPL *doesn't*, that omission is the signal.
    -   **Signal:** Divergence from the sector trend.
    -   **Adjudication:** "Sector Outlier".

## Proposed Architecture: The "Adjudicator" Pipeline

We can replace the simple `scoring.py` with a multi-agent "Adjudicator":

1.  **The Quant Agent:** Calculates Price Velocity & Volatility around the filing timestamp.
2.  **The Linguist Agent:** Calculates Diff Similarity & Fog Index.
3.  **The Historian Agent:** Checks if this event (e.g., "CFO Resignation") historically caused a drop for *this specific stock*.

### Example Output in Dashboard

Instead of:
> *8-K: No details 🟡 Possibly related*

We generate:
> *8-K: **Critical** 🔴 (Score: 0.95)*
> * **Market Reaction:** Price dropped 2.4% within 15 mins of filing.*
> * **Risk Drift:** 40% change in "Risk Factors" vs. last quarter.*
> * **Context:** "Departure of Directors" (Historical impact: -1.2%)*
