# UI Specification — CareerTwin

## Visual direction

CareerTwin uses a **premium dark technical/editorial aesthetic**. It must feel
like a premium technical product, not a CRUD dashboard or a generic AI SaaS
site.

### Required characteristics
- Near-black base background (`#050507`)
- Subtle technical grid/detail texture where appropriate
- Thin borders
- Restrained accent color (a single, muted technical accent)
- Mixed display (headings) + technical/monospaced metadata typography
- Asymmetric editorial compositions
- Large visual sections
- Floating informational panels
- Selective 3D only for future visual experiences
- Purposeful motion (page entrance, section reveal, navigation transitions)
- Responsive / mobile-first composition

### Explicitly prohibited
- Generic admin dashboard appearance
- Excessive cards
- Excessive rounded containers
- Rainbow gradients
- Excessive glassmorphism
- Fake AI activity animations
- Unnecessary continuous 3D
- Animation used merely for decoration
- "Everything rounded" SaaS-card styling

## Motion
Motion (framer-motion) is used only for meaningful transitions:
- page entrance
- section reveal
- navigation transitions
- upload/processing states
- review transitions
- confirmation

No unnecessary continuous animations.

## Main routes and purpose

| Route | Purpose |
|-------|---------|
| `/` | Landing page: "YOUR CAREER. UNDERSTOOD." Introduces the system |
| `/auth/login` | Sign in (placeholder; auth connects later) |
| `/auth/signup` | Create account (placeholder; auth connects later) |
| `/onboarding/start` | Choose manual profile or resume upload (implemented) |
| `/onboarding/resume` | Upload resume → extract text → structured draft → save (implemented) |
| `/onboarding/profile` | Manual profile form: basic info, education, skills, projects, experience, career goals (implemented) |
| `/onboarding/review` | Inspect structured profile before confirmation (implemented) |
| `/app` | Application shell index |
| `/app/twin` | Confirmed CareerTwin overview (implemented) |
| `/app/careers` | Career path analysis (future) |
| `/app/skills` | Skill intelligence (future) |
| `/app/roadmap` | Learning roadmap (future) |
| `/app/interview` | Interview lab (future) |
| `/app/trust` | Evidence intelligence / confidence (future) |

## Onboarding flow (Phase 2)

1. **Start** (`/onboarding/start`): choose "Build manually" or "Upload resume".
2. **Manual** (`/onboarding/profile`): progressive sections with add/remove
   repeated items; client-side validation; draft auto-saves.
3. **Resume** (`/onboarding/resume`): select file → upload → extracted text →
   structured draft → save draft profile. Extraction is deterministic; no fake
   AI agent activity is shown.
4. **Review** (`/onboarding/review`): professional verification interface
   displaying personal info, education, skills, projects, experience, and
   career goals. Extracted info is labeled by source
   (USER_CONFIRMED / DOCUMENT_EXTRACTED / SYSTEM_INFERRED).
5. **Confirm**: "CONFIRM CAREERTWIN" validates, persists, sets status to
   `CONFIRMED`, redirects to `/app/twin`.
6. **Twin** (`/app/twin`): overview displaying name, headline, summary,
   education overview, skill/project/experience counts, career goal, and
   profile status.

## Navigation (future persistent shell)

```
CAREERTWIN

01 TWIN
02 CAREERS
03 SKILLS
04 ROADMAP
05 INTERVIEW
06 TRUST

PROFILE ↗
```

Designed to become a persistent application shell. For now, placeholder pages
are sufficient.
