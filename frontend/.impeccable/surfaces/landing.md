---
version: 1
slug: "landing"
primary_target: "app/page.tsx"
related_targets: []
---

# Landing (public)

Mode: Persuade. Visitor: a judge, an institution admin or a prospective verifier deciding whether to sign in, verify a record or register.

THESIS: A plain-spoken civic notice board. It says what the platform does in one sentence, shows the four-step flow, and states the one promise that matters: it flags and routes, it never rejects.

OWN-WORLD: Same cool neutrals and verdigris accent as the app. One quiet hero visual: a CSS/SVG waymark line (four nodes joined by a path) that draws once and respects reduced motion. No gradients, no WebGL, no stock imagery, no official marks.

STORY: Read the sentence, follow upload -> checks -> review -> verification, see Clear/Alert/Excess with icon and word, then pick Sign in, Verify a record or Register as verifier.

STRUCTURE: Header (name, language, theme, sign in). Hero with copy and the waymark line. Flow stepper (ordered list). Three status states. Principle band ("advisory, never rejects"). Three entry paths. Footer with the prototype notice, always visible.

CONSTRAINTS: No layout shift (fixed-size visual, fonts via next/font). en/hi without login, stored locally. Light and dark. Prototype and synthetic-data notice stays visible. Smooth scroll via CSS only (scroll-behavior, reduced-motion off); no library.
