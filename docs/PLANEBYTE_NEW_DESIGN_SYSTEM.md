# PlaneByte workspace design system

Implemented November 15, 2026 in `dashboard/app/planebyte-workspace.css` with the existing local PlaneByte Sans files and brand mark. The supplied Pastel screenshots guide density, framing and contextual panels. PlaneByte retains its own identity, routes, prices and actual product availability.

## Tokens and layout

- Surfaces: warm neutral canvas, white framed workspace, delicate #e7e7e8 separators; dark appearance preserves the existing theme preference.
- Ink #20242c, supporting text #646970, PlaneByte blue #2175cf; AI uses restrained violet. Coral, mint, lilac and peach identify graph categories rather than business status.
- Spacing: 4 / 8 / 12 / 16 / 24 / 32px. Expanded sidebar 228px, collapsed 72px; compact 60px header. Desktop content 24px, wide-screen 28×32px, mobile 18×14px.
- Type: 26px page titles, 17px sections, 13–14px body, 11–12px metadata. The home headline scales to 34px. Local fonts avoid an external font dependency.
- Framing: 20px outer workspace, 14px panels, 9–10px controls; status semantics remain separate from the pastel category palette.

## Reusable behavior

`CommandCentre` passes a draft question into the real private assistant. It never silently submits a model call. `Conversation` backs both the drawer and the focused AI workspace. `UnifiedSettingsWorkspace` hosts existing forms and authorization. `Modal` supports an evidence drawer retaining result filters. `SignalCard` and `SignalTable` retain ordinary links and optionally open that drawer.

The graph has eight bounded categories and at most five visible related values per category, with zoom, fit, collapse, search and a structured alternative. Actual values and source uncertainty remain inspectable. No animation or illustration is evidence of a running integration.

## Responsive and accessible contract

390 / 768 / 1024 / 1440 / 1920px plus 320 / 1280px regression checks are required. Navigation becomes a focus-managed mobile drawer; settings navigation scrolls horizontally on mobile. Graph details stack below its canvas on smaller screens. Evidence drawers become nearly full-screen and keep a keyboard close control. Reduced-motion preferences are respected. The graph's adjacent buttons provide a non-spatial navigation path.

Browser and visual acceptance results are recorded separately; these tokens are not an accessibility certification.
