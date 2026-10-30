# Agents — CareerTwin

CareerTwin uses approximately six specialized agents. Agents are invoked
selectively — a request should not pull in every agent by default.

## Selection principle

A request asking about missing ML engineering skills should not execute the
Learning Agent or Interview Agent unless necessary. Only the agents relevant
to the specific task should run.

## The six agents

### 1. Profile Agent
- **Purpose:** Build and maintain the user's CareerTwin profile from onboarding
  input (manual entry or resume import).
- **Inputs:** raw onboarding data, resume text (future), existing profile state
- **Outputs:** structured profile fields (education, skills, projects,
  experience, interests, goals)
- **Tools it may eventually use:** profile validation service, resume parser
  (future), storage service
- **What it should NOT do:** career recommendations, interview evaluation,
  evidence verification
- **When invoked:** during onboarding and when the user updates their profile

### 2. Career Agent
- **Purpose:** Analyze plausible career directions for a given CareerTwin and
  surface the gaps between current state and target roles.
- **Inputs:** CareerTwin profile, career path data, market data (future)
- **Outputs:** career path options, fit analysis, identified gaps
- **Tools it may eventually use:** skill-gap mathematics service, career
  paths data
- **What it should NOT do:** build learning plans, run interviews, verify
  evidence
- **When invoked:** when the user explores careers or requests path analysis

### 3. Skill Gap Agent
- **Purpose:** Compute the gap between the user's evidenced skills and the
  skills required for a target role.
- **Inputs:** user skills, target role skill requirements
- **Outputs:** skill-gap list with missing/under-evidenced skills
- **Tools it may eventually use:** skill-gap mathematics service (deterministic)
- **What it should NOT do:** generate learning content, conduct interviews
- **When invoked:** after a career target is selected, before a roadmap is built

### 4. Learning Agent
- **Purpose:** Produce a personalized, ordered learning plan that closes
  identified skill gaps.
- **Inputs:** skill-gap results, user preferences, available resources
- **Outputs:** learning plan with learning items and milestones
- **Tools it may eventually use:** learning resources catalog, retrieval
- **What it should NOT do:** verify evidence, evaluate interviews, recommend
  careers
- **When invoked:** after skill gaps are known and the user wants a roadmap

### 5. Interview Agent
- **Purpose:** Run adaptive interview preparation grounded in the user's
  experience and target role.
- **Inputs:** user profile, target role, interview history
- **Outputs:** interview questions, session structure, performance feedback
- **Tools it may eventually use:** interview evaluation service
- **What it should NOT do:** build profiles, verify evidence, run RAG retrieval
- **When invoked:** when the user enters interview preparation for a role

### 6. Evidence Agent
- **Purpose:** Verify claims against evidence sources, detect contradictions,
  and assign claim-level confidence classifications.
- **Inputs:** claims, evidence sources, retrieved chunks
- **Outputs:** confidence classification (SUPPORTED/INFERRED/UNCERTAIN/
  CONTRADICTED), evidence references
- **Tools it may eventually use:** RAG retrieval, confidence engine (deterministic)
- **What it should NOT do:** build profiles, recommend careers, run interviews
- **When invoked:** when information needs to be verified before being trusted

### 7. Interview Agent (Phase 7 — implemented)
- **Purpose:** Orchestrate adaptive interview sessions with deterministic
  question selection, difficulty progression, and skill performance tracking.
- **Inputs:** CareerTwin profile, target career, interview mode, difficulty
- **Outputs:** interview session, next question, evaluation results, skill
  performance summary, interview summary
- **Tools it may use:** create_interview_session, get_interview_session,
  get_next_interview_question, submit_interview_answer,
  evaluate_interview_answer, get_interview_results
- **What it should NOT do:** build profiles, recommend careers, verify evidence
- **When invoked:** when the user enters interview preparation for a role
- **Deterministic responsibilities:** session state, question selection,
  difficulty progression, scoring aggregation, completion, skill performance
- **LLM responsibilities:** question wording, qualitative evaluation, feedback
  generation

## Invocation rules
- Agents are tools, not the whole application.
- Do not add a chatbot just for demonstration.
- Do not add fake agent traces or fake confidence values.
- Deterministic services own validation, storage, calculations, retrieval,
  confidence, authorization, persistence, and traces.
