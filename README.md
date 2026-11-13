# Transfer-Aware AI Coaching for Independent Interview Skill Development

An intelligent, multi-stage interview training and cognitive coaching system designed to measure, diagnose, and develop deep technical problem-solving competencies beyond surface pattern matching.

---

## 1. System Overview

Traditional technical interview preparation platforms rely on rote memorization or shallow answer matching. This platform integrates **Cognitive Transfer Theory** and **Socratic Scaffolding** into automated interview coaching:

1. **Resume Intelligence**: Parses candidate CVs, extracts verifiable technical claims, normalizes taxonomies, and constructs grounded candidate competency profiles without hallucinating unverified experience.
2. **Role-Aware Interview Engine**: Dynamically orchestrates multi-stage interview assessments (Orientation, Core Technical, Dynamic Inquiries, and Architectural Gauntlets) calibrated to candidate target roles and experience tiers.
3. **Turn-Level Evaluation & Diagnosis**: Performs rubric-grounded scoring, extracts core engineering invariants, detects surface-pattern leakage, and diagnoses conceptual gaps.
4. **Transfer-Aware Coaching Loop**: Generates invariant-preserving problem variants across progressive transfer distances (L0 Recall to L5 Complex Distant Transfer), fading assistance ladders (High Scaffold → Independent Transfer) to cultivate genuine mastery.
5. **Interactive Coaching Workspace**: Unified frontend studio featuring conversational tutoring, guided practice, and live feedback.

---

## 2. Technology Stack

- **Backend**: Python 3.11, [FastAPI](https://fastapi.tiangolo.com/), Pydantic v2, SQLAlchemy 2.0 (Asyncio)
- **Database**: SQLite (local persistence with asynchronous WAL mode via `aiosqlite`)
- **AI & Evaluation**: Plug-and-play provider architecture (NVIDIA NIM, DeepSeek, Local / Structured Heuristics) with deterministic fallbacks
- **Frontend**: React 18, TypeScript, [Vite](https://vitejs.dev/), TailwindCSS / Vanilla CSS, Lucide Icons, React Router v7

---

## 3. Project Architecture

```text
AI-Interview-Coach/
├── ai/                         # AI prompts, evaluators, extractors, and transfer generators
│   ├── coaching_engine/        # Socratic hint laddering & assistance fading
│   ├── diagnosis_engine/       # Error classification & invariant violation detectors
│   ├── interview_engine/       # Multi-stage interview generation & follow-up reasoning
│   ├── resume_engine/          # Document parsers, rule extractors & claim normalizers
│   └── transfer_engine/        # Far-transfer variant generation (L0 - L5)
├── backend/                    # FastAPI application, domain services, and persistence
│   ├── api/v1/endpoints/       # REST endpoints (candidates, interviews, coaching, research)
│   ├── domain/                 # Domain logic, blueprints, and transfer taxonomy
│   ├── models/                 # SQLAlchemy ORM models
│   ├── repositories/           # Asynchronous data access layer
│   └── services/               # Orchestration & business logic
├── frontend/                   # Modern React TypeScript SPA
│   ├── src/components/         # Studio interfaces (Interview, Coaching, Resume, Roadmap)
│   ├── src/features/           # Feature workspaces & coaching panels
│   ├── src/layouts/            # App shell and layout containers
│   ├── src/pages/              # Route view components
│   └── src/services/           # Backend API integration client
├── requirements.txt            # Python dependencies manifest
├── .env.example                # Configuration template
└── README.md                   # System documentation
```

---

## 4. Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ and `npm`

### Backend Setup
1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
2. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```powershell
   copy .env.example .env
   # Set DATABASE_URL=sqlite+aiosqlite:///./ai_interview_coach.db
   # Optional: set NVIDIA_API_KEY for cloud model inference
   ```
4. Start the backend server:
   ```powershell
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```powershell
   cd frontend
   npm install
   ```
2. Run the development server:
   ```powershell
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser.

### Production Build
```powershell
npm run build --prefix frontend
```
