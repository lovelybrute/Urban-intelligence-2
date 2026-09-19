# SIH 26124 interface redesign

The platform now uses a dark teal operations theme with a map-led landing page, grouped navigation, and an overview focused on reviewing detections.

## Changes
- Landing page with an explicitly labelled sample Hyderabad map, sensing workflow, and links to existing modules.
- Overview with data-derived metrics, searchable and priority-filtered detection feed, road condition cards, and evidence inspection links.
- Grouped, collapsible desktop sidebar; mobile drawer with focus containment, Escape dismissal, and focus restoration.
- Compact map layer controls and map resizing when its container changes.
- Demo scenarios add simulated events and alerts; deduplication updates observations locally.
- Backend errors propagate to the retry banner instead of silently replacing backend data with mock data.
- Removed assumed FPS/camera values from the redesigned overview, header, sidebar, and map popups.

## Validation
- `cd frontend && npm ci && npm run build`: TypeScript and production bundle passed.
- Isolated jsdom interaction checks passed: metrics, scenario insertion, search empty state, landing/dashboard navigation, mobile drawer and Escape.
- Backend-unavailable interaction check passed: retry shown, no mock detections inserted.
- Full browser visual/responsive verification could not run in the editing environment: local browser startup failed and cloud browser blocked localhost. Desktop and phone visual checks remain necessary.
- No backend service or ML training was run. Existing specialist modules retain their domain logic and demo content.

## Run
Use the existing `npm run dev` workflow in `frontend`. Demo mode remains the default. Set `VITE_DEMO_MODE=false` and the existing API URL configuration to use the backend. The redesign does not deploy a website or train models.
