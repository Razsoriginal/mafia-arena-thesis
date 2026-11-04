# Taste

- Wants experiment/agent runs executed in parallel (multiple processes/workers) so long runs finish quickly, rather than accepting slow sequential execution. Confidence: 0.6
- Specifies each model role with its own provider and credentials, and expects them kept strictly separate — no silent provider precedence, key borrowing, or fallback endpoints across roles (e.g. main backbone on AiCredits, gate model on OpenRouter only). Confidence: 0.75
