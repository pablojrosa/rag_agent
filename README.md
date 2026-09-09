# RAG Control Panel with OpenAI and Langfuse

A Flask and React assistant for *An Introduction to Statistical Learning with
Applications in Python*. Pinecone retrieves book passages, OpenAI generates
answers, PostgreSQL stores conversations, and Langfuse owns telemetry and
evaluation results. Evaluation analysis is handled in Langfuse rather than in the
application UI. No local background evaluation thread is required.

## Architecture

For a visual, technical architecture map of the complete system, open the
[Architecture Guide](docs/architecture.html) in a browser. It covers the request
lifecycle, book RAG flow, Langfuse evaluation loop, data ownership, and repository
entry points.

- `backend/main.py`: HTTP validation, chat transactions, and dashboard routes.
- `backend/src/app/rag_service.py`: shared retrieval and generation pipeline.
- `backend/src/app/rag_tool.py`: embeddings and structured Pinecone passages.
- `backend/src/app/main_agent.py`: OpenAI Responses generation, query rewriting,
  chart artifacts, and Langfuse-managed prompts.
- `backend/src/app/observability.py`: optional Langfuse observations and sessions.
- `backend/src/app/monitoring.py`: server-side Langfuse dashboard adapter.
- `backend/setup_langfuse.py`: repeatable score/evaluator/rule setup.
- `backend/create_golden_dataset.py`: publish reference questions to Langfuse.
- `backend/run_evaluations.py`: dataset experiments using the shared pipeline.
- Langfuse Cloud: traces, scores, evaluator results, datasets, and experiments.

The chat UI includes a left conversation sidebar. PostgreSQL stores conversations
and messages; deleting a conversation applies a soft delete (`deleted=true`) so
the user's history is hidden while audit data and Langfuse traces are preserved.

The chat response can also include validated visual artifacts. When a chart adds
value, the model returns an `artifacts` array alongside the text response. Each
artifact is a data-only specification (`bar`, `line`, `scatter`, or `pie`); React
renders it as SVG and never executes model-generated HTML or JavaScript. The
backend filters invalid chart types, oversized datasets, and malformed points.

A chat trace contains `chat-request`, `rag-answer`, `query-embedding`,
`book-retrieval`, `answer-generation`, `save-conversation`, and, when applicable,
`query-rewrite` and `create-chart`. The `rag-answer`
observation contains question, retrieved context, and output together so a judge
can evaluate it without reading sibling spans. Experiment observations also carry
an expected answer. Sessions group chat turns; the outer trace records the saved
assistant message ID. Generation observations include token usage for Langfuse
cost calculation. Retrieved chunks retain source, page, ID, text, and similarity.

Telemetry includes question/answer content, retrieved passages, and generation
history. Credentials and database URLs are not deliberately included in traces.
`LANGFUSE_ENABLED=false` disables instrumentation and dashboard access. Missing
credentials leave chat functional. Export failures do not replace application
errors or prevent a response. The SDK batches exports; short-lived scripts flush
before exiting. Telemetry is best effort and can be lost on abrupt termination.

## Local setup

Install Python 3.13 and Node.js 22.12+; start PostgreSQL and create a database.
Prepare a Pinecone index containing the book embeddings.

```sh
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

For an existing installation, keep your `.env` and add the new variables from
`.env.example`. An existing Google API key is no longer used.

Configure `OPENAI_API_KEY`, Pinecone credentials/index, and `DATABASE_URL`, then:

```sh
flask --app main db upgrade
python main.py
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. The backend listens on http://localhost:5001.
Pinecone is initialized on first retrieval, so migrations do not need its service.
The frontend still sends conversation history; PostgreSQL is not used to rebuild
that history. Retrieval uses the current question only.

## Connect Langfuse

Use Langfuse Cloud or a compatible v4 server. This repo pins Python SDK 4.15.1 and
uses Observations v2, Scores v3, and Experiments APIs. Older servers may not expose
these endpoints. Configure:

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENVIRONMENT=development
LANGFUSE_PROJECT_ID=your-project-id
```

Use the base URL for your project's region. Keep service keys on the backend.
Restart Flask after changing environment variables.

In Langfuse Project Settings, configure an **LLM Connection** for the judge. Its
provider name must match `LANGFUSE_JUDGE_PROVIDER` (default `OpenAI`). This is a
separate project configuration from the application's OpenAI key; the setup script
does not upload that key. Judge calls consume the configured provider's quota.

Then run:

```sh
python setup_langfuse.py
python create_golden_dataset.py
python run_evaluations.py --concurrency 2
# Optional small smoke experiment
python run_evaluations.py --name smoke-check --limit 2 --concurrency 1
```

To migrate existing reference questions instead of bundled examples:

```sh
python create_golden_dataset.py --from-postgres
```

Dataset item IDs are derived from dataset name and question, making repeat uploads
update the same items. The bundled examples should be reviewed for book coverage
before using them as a quality benchmark. Experiments run every active dataset
item, rather than a fixed five-row sample.

## Prompt management

The production prompts `book-answer` and `query-rewrite` are loaded from Langfuse
Prompt Management using `LANGFUSE_PROMPT_LABEL` (default `production`). Langfuse
prompt versions and labels are recorded on each generation observation. The SDK
cache is controlled by `LANGFUSE_PROMPT_CACHE_TTL`; local prompt text is used as a
fallback if Langfuse is unavailable. Create both prompts as text prompts in the
project before switching the label away from the local fallback.

## Evaluation definitions

The setup script creates numeric 0–1 score definitions and observation evaluators:

| Score | Purpose | Rules |
|---|---|---|
| `groundedness_v1` | Claims supported by retrieved context | Online and offline |
| `relevance_v1` | Response addresses the question | Online and offline |
| `correctness_v1` | Response agrees with reference answer | Offline only |

Rules match `rag-answer`, mode, and environment. Online sampling defaults to 10%;
offline sampling is 100%. Set `LANGFUSE_ONLINE_EVAL_SAMPLE_RATE=1` **before initial
setup** to score every online answer during validation. Existing definitions and
rules are preserved on reruns; edit them in Langfuse or create a new version to
change a rubric, model, or sampling policy. Rule execution is asynchronous, so a
completed experiment can appear before its scores.

Score configurations describe names and scales; evaluators produce values. Adding
an active configuration and an evaluator in Langfuse makes the metric available to
the dashboard without a new React column. `DASHBOARD_SCORE_NAMES` optionally limits
visible names. Numeric, boolean, categorical, and structured values are rendered;
hover over headers for descriptions and expand reasoning on individual scores.
Version metric names when changing criteria. New judge scores are not numerically
interchangeable with historical evaluator results.

## Langfuse evaluation behavior

Evaluation metrics are intentionally managed and visualized in Langfuse. The React
application exposes the chat experience only; it does not render online or offline
evaluation dashboards. Use the Langfuse project UI for trace inspection, score
exploration, golden dataset experiments, comparisons, and cost/token analysis.

The backend monitoring adapter and routes remain available for compatibility and
future integrations, but they are not linked from the frontend navigation.

- `GET /conversation-metrics?days=7&cursor=...` reads online observations and scores.
- `GET /offline-evaluation-results?days=7&experiment_id=...&cursor=...` reads runs and
  experiment items for `LANGFUSE_DATASET_NAME`.
- Each page contains up to 20 items, with cursor pagination. The experiment picker
  displays up to 50 recent runs in the chosen period (1–90 days).
- The online performance table uses the Metrics API for full-period operation counts,
  average durations, tokens, and costs.
- Quality metric cards show **averages on the displayed page**, not full-run statistics.
  Comparison displays the first page of the second experiment. Use Langfuse for
  complete-run quality analysis and detailed cost/token dashboards.
- Missing scores display `No score available`, never zero. This can mean pending,
  excluded by sampling, or evaluation failure; the public score result alone does
  not distinguish those states. Refresh to fetch newly available results.
- Missing credentials produce a configuration state; provider failures return 503.
- `LANGFUSE_PROJECT_ID` enables links to the detailed trace (Langfuse login required).

PostgreSQL remains the conversation store. Historical evaluation/reference tables
and migrations are retained to preserve data, but the chat and dashboards no longer
write/read the old evaluation tables. No destructive database migration is needed.

## Validation

```sh
cd backend
.venv/bin/python -B -m unittest discover -s tests -v
```

```sh
cd frontend
npm run lint
npm run build
```

After connecting Langfuse, send a book question, inspect its nested observations,
check token usage, wait for scores, and refresh the dashboard. Run two experiments
with distinct names to test comparison. Disable Langfuse and confirm chat still
works. Local tests use mocked providers and an in-memory database.

## Deployment

The backend Dockerfile applies database migrations and starts Gunicorn using
`PORT`. Set the service root to `backend/`, configure the same environment variables,
and set `ALLOWED_ORIGINS` to the deployed frontend origin. The frontend uses
`VITE_API_URL`, defaulting to the local backend URL during development.

## References

- [Langfuse Python SDK](https://langfuse.com/docs/observability/sdk/overview)
- [Observation evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Experiments](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Scores API](https://langfuse.com/docs/api-and-data-platform/features/scores-api)
