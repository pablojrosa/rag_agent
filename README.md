# Scanntech Challenge
# RAG Control Panel with Gemini and Quality Metrics 🚀

This project was built as part of a technical challenge proposed by Scanntech. It is primarily a **RAG** (Retrieval-Augmented Generation) chatbot that answers questions about the book "An Introduction to Statistical Learning with Applications in Python".

Beyond being a simple chatbot, the project also includes a **Control Panel** to monitor, evaluate, and improve the quality of the RAG system through real-time metrics and on-demand deep evaluations.

## Preview

![Panel de Control RAG](media/panel_de_control.png) 

## Table of Contents

- [RAG Control Panel: Main Features](#rag-control-panel-main-features)
- [Dual Evaluation System](#dual-evaluation-system)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Railway Deployment with Docker](#railway-deployment-with-docker)

## RAG Control Panel: Main Features

The application is presented as a dashboard with three main sections, designed to interact with the agent and analyze its performance.

### 1. Interactive Chat
A chat interface built with React that allows users to talk to the agent. It includes:
- **Conversation Memory**: The chat history is sent to the agent to preserve context.
- **Semantic Search**: The agent uses Pinecone to search the book and ground its answers in retrieved information.
- **Conversation Persistence**: All messages from both user and agent are stored in a PostgreSQL database.

### 2. Conversation Metrics (Online Metrics)
A table view that shows quality metrics for real user conversations, computed in real time.
- **Automatic Evaluation**: Each bot response is evaluated in the background so the user experience is not affected.
- **Key Metrics**: The system tracks `faithfulness` (to detect hallucinations) and `answer_relevancy`.
- **Full Context**: The table shows the user's question, the bot's answer, and their respective scores for quick diagnosis.

### 3. System Evaluation (Offline Monitoring)
A section dedicated to running a deep, controlled evaluation of the RAG system.
- **Golden Dataset**: Uses a curated set of question/answer pairs stored in PostgreSQL.
- **Offline Execution**: Provides a UI for reviewing the results of a script that runs the full evaluation dataset against the RAG system.
- **Full Report**: Displays advanced metrics such as `context_precision`, `context_recall`, and `answer_correctness`, making it possible to validate retrieval and generation quality objectively.

## Dual Evaluation System

The core of this project is not only the conversational interface, but also the ability to evaluate answers with **Ragas** through two complementary evaluation loops:

- **Online Metrics:** Provides continuous visibility into bot performance in production by detecting issues in real conversations through reference-free metrics.
- **Offline Monitoring:** Allows developers to measure system quality in a controlled environment, compare prompt versions, and validate improvements before deployment.

## Technology Stack

- **Frontend**:
  - **Library/Framework**: React, Vite
  - **Styling**: Plain CSS

- **Backend**:
  - **Framework**: Python, Flask
  - **Relational Database**: PostgreSQL
  - **ORM and Migrations**: SQLAlchemy, Flask-Migrate
  - **WSGI Server**: Gunicorn

- **AI**:
  - **Language Model**: Google Gemini (`gemini-2.0-flash`)
  - **Vector Database**: Pinecone
  - **Embedding Model**: OpenAI (`text-embedding-3-small`)
  - **RAG Evaluation Library**: Ragas

- **Deployment**:
  - **Platform**: Railway
  - **Containerization**: **Docker**

## Project Structure

The project is organized as a monorepo with two main directories:

```
/
├── backend/                       # Flask server code
│   ├── data/                      # Source book PDF
│   ├── src/
│   │   ├── app/                   # Application logic, models, and tools
│   │   └── services/              # Utility services such as vectorize_pdf.py
│   ├── migrations/                # Database migration scripts
│   ├── Dockerfile                 # Production Docker setup
│   ├── .dockerignore              # Excludes unnecessary files from the Docker image
│   ├── main.py                    # Flask application entrypoint
│   ├── run_evaluations.py         # Offline evaluation script
│   ├── create_golden_dataset.py   # Golden dataset seeding script
│   └── requirements.txt
│
├── frontend/                      # React application code
│   ├── src/
│   │   ├── api/                   # Backend API helpers
│   │   ├── components/            # Components, pages, and styles
│   │   ├── App.jsx                # Route orchestrator
│   │   └── main.jsx               # React application entrypoint
│   └── ...
├── media/                         # Supporting assets
├── .gitignore
└── README.md
```

## Railway Deployment with Docker

This project is designed to be deployed consistently on **Railway** using **Docker**. Containerization ensures the runtime environment is identical everywhere, avoiding system dependency issues such as requiring `git` for the `ragas` library.

### Railway Setup

1.  **Create the Project**: Push your repository to GitHub and create a new Railway project from it.
2.  **Add the Database**: Inside the Railway project, add a new **PostgreSQL** service. Railway will automatically inject the `DATABASE_URL` environment variable into your other services.
3.  **Configure Environment Variables**: In the `backend` service, open the "Variables" tab and configure the following secrets:

    ```ini
    # Google API key for Gemini
    GOOGLE_API_KEY="your_google_key"

    # Pinecone API key
    PINECONE_API_KEY="your_pinecone_key"

    # OpenAI API key (used for embeddings)
    OPENAI_API_KEY="your_openai_key"
    
    # Allowed CORS origins (your deployed frontend URL)
    ALLOWED_ORIGINS="https://your-frontend.up.railway.app"
    ```

4.  **Set the Root Directory (Important)**: Since this is a monorepo, Railway needs to know where the backend lives. In the `backend` service `Settings`, under `Build`, set the **Root Directory** to `backend/`.

5.  **Deploy**: Once the variables and root directory are configured, any `git push` to your main branch will trigger a new deployment. Railway will detect the `Dockerfile` in `backend/`, build the image, and put it online. The `CMD` instruction in the `Dockerfile` applies migrations (`flask db upgrade`) and then starts the server (`gunicorn main:app`).
