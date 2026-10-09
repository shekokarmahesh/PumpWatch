# PumpWatch UI sources

The October 2026 UI refresh uses a dark green-neutral palette, mint actions, bento scenario cards, shared-layout navigation, spring press feedback, animated scores, and a consistent report/evidence layout. The scoring pipeline and evidence remain unchanged.

## Source used in code

[beUI](https://beui.dev): `AnimatedNumber`, `TiltCard`, and shared spring/easing tokens were adapted into `frontend/src/components/ui/motion.tsx`. Upstream: [starc007/ui-components](https://github.com/starc007/ui-components). Adaptations replace Tailwind and path aliases with project CSS, limit tilt to three degrees and mouse pointers, provide stable accessible score labels, and respect reduced motion. The upstream MIT copyright and license are retained in `frontend/src/components/ui/LICENSE.beui`.

Motion is installed as a runtime dependency. Buttons and section reveals are project components using the same motion tokens. No paid beUI Pro source is included.

DM Sans and Space Grotesk are self-hosted from Google Fonts. Their SIL Open Font License files are included alongside the font assets in `frontend/public/assets/fonts`; rendering does not require a Google Fonts request.

## Design references consulted

- [Kobra](https://kobra.systems): restrained component surfaces and navigation hierarchy.
- [Beautiful UI](https://www.beautifului.dev/): feedback and loading presentation.
- [Kinetics](https://kinetics.colorion.co): purposeful spring interactions.
- [Transitions](https://transitions.dev): concise content entrances.
- [Astryx](https://astryx.atmeta.com): consistent theme and component tokens.
- [Evil Charts line chart](https://evilcharts.com/docs/recharts/line-chart/static): gradient chart presentation and selectable series legends. The implementation stays on the existing Recharts dependency; no Evil Charts source is vendored.
- [Reverse UI](https://reverseui.com): modern card composition and restrained visual depth.

These references informed styling; they are not all installed dependencies. Paid components were not purchased or copied.

## Data presentation

The orbit illustration is decorative and contains no invented stock measurements. Charts only show API history, keep missing values as gaps, and explain single-day histories. Hype and support can be toggled independently; the accessible observation table always retains both values. Fictional replay labels remain visible throughout the app.
