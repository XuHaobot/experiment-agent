# Agent Notes

This project is a minimal Python + Streamlit skeleton for an experiment log整理 Agent.

## Development Principles

- Keep the first version simple and local-first.
- Prefer clear Python functions over heavy Agent frameworks.
- Store records as JSON in `data/records/`.
- Store reports as Markdown in `data/reports/`.
- Keep tools small and focused.
- Do not add databases, Docker, vector stores, auth, or multi-user features in the MVP.

## Main Command

```bash
streamlit run app.py
```

## Expected Flow

1. Read uploaded text.
2. Let `ExperimentAgent` decide which tools to call.
3. Merge tool outputs into one experiment record.
4. Save JSON and Markdown locally.
5. Query history with simple keyword search.
