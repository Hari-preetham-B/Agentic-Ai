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
- future agent execution visualization

No unnecessary continuous animations.

## Main routes and intended future purpose

| Route | Purpose |
|-------|---------|
| `/` | Landing page: "YOUR CAREER. UNDERSTOOD." Introduces the system |
| `/auth/login` | Sign in (placeholder; auth connects later) |
| `/auth/signup` | Create account (placeholder; auth connects later) |
| `/onboarding/start` | Begin onboarding (placeholder) |
| `/onboarding/resume` | Resume import (placeholder; later phase) |
| `/onboarding/profile` | Manual profile entry (placeholder) |
| `/onboarding/review` | Onboarding review (placeholder) |
| `/app` | Application shell index |
| `/app/twin` | The CareerTwin professional state |
| `/app/careers` | Career path analysis |
| `/app/skills` | Skill intelligence |
| `/app/roadmap` | Learning roadmap |
| `/app/interview` | Interview lab |
| `/app/trust` | Evidence intelligence / confidence |

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
