# Copilot instructions for this repository

## Build, test, and lint commands

- Use **pnpm** with **Node 22.12+**.
- Install dependencies: `pnpm install`
- Start local dev server: `pnpm dev`
- Run the standard validation pass: `pnpm validate`
- Lint: `pnpm lint`
- Type-check Astro/TypeScript: `pnpm check`
- Build production output: `pnpm build`
- Check formatting: `pnpm format:check`
- Fix formatting: `pnpm format`

### Test commands

- Unit tests: `pnpm test`
- Run Vitest once instead of watch mode: `pnpm test -- --run`
- Run a single Vitest file: `pnpm test -- --run path/to/file.test.ts`
- Run a single Vitest test by name: `pnpm test -- --run -t "test name"`
- E2E tests: `pnpm test:e2e`
- Run a single Playwright spec: `pnpm test:e2e -- path/to/spec.ts`

At the moment, no `*.test.*`, `*.spec.*`, or Playwright spec files are committed, so the test scripts currently report "No tests found".

## High-level architecture

- This is an **Astro 6 static site** with a small server-side surface for form handlers and generated assets. The repo still carries Velocity starter branding in `README.md`, but the active site is the French-language **Backstage** implementation configured in `src/config/site.config.ts`, `src/config/nav.config.ts`, and the page content under `src/pages/`.
- `src/layouts/BaseLayout.astro` is the root shell for almost everything. It pulls in global styles, SEO tags, JSON-LD, analytics, the consent banner, the favicon/manifest, and Astro view transitions. Higher-level layouts such as `PageLayout.astro`, `BlogLayout.astro`, `MarketingLayout.astro`, and `LandingLayout.astro` mainly decide how Header/Footer are composed around that base shell.
- Structured site data is centralized:
  - `src/config/site.config.ts` drives metadata, branding, canonical site URL, verification tags, and manifest colors.
  - `src/config/nav.config.ts` drives Header/Footer navigation instead of deriving menus from filesystem routes.
  - `src/config/consent.config.ts` drives both the consent banner UI and analytics consent behavior.
- Content is wired through **Astro content collections** in `src/content.config.ts`. The blog, pages, authors, and FAQ collections all have schemas, and downstream consumers assume that shape:
  - blog index and `[...slug].astro` routes
  - RSS generation in `src/pages/rss.xml.ts`
  - OG image generation in `src/pages/og/[...slug].png.ts`
  The current build tolerates empty collections and emits warnings rather than failing.
- Styling is built around **Tailwind CSS v4 + CSS custom properties**. `src/styles/global.css` imports token files from `src/styles/tokens/` and maps them into Tailwind's `@theme`. Theme variants live in `src/styles/themes/`. Dark mode is controlled by a `dark` class added early in `BaseLayout.astro`.

## Key conventions

- Prefer changing **config files over component internals** for site-wide behavior. Branding, canonical URLs, manifest colors, nav items, consent copy, consent categories, and verification tags are all expected to come from `src/config/*`.
- Use the `@/*` path alias for imports from `src/`.
- UI and layout primitives usually follow the same structure:
  - main Astro component (`Component.astro`)
  - companion variant definitions (`component.variants.ts`) built with `class-variance-authority`
  - `cn()` from `src/lib/cn.ts` to merge Tailwind classes
  Keep that pattern when extending existing components.
- Many components are **slot-driven** rather than prop-heavy. `Hero`, `Header`, and `Footer` expose named slots and variant props; preserve those composition patterns instead of hardcoding page-specific markup into the shared components.
- When adding environment variables, declare them in `astro.config.mjs` under the `env.schema` and consume them through `astro:env/server` or `astro:env/client`. The analytics and consent flow depends on that typed env setup.
- Analytics and consent are intentionally coupled. `src/components/layout/Analytics.astro` and `src/components/ui/overlay/ConsentBanner/ConsentBanner.astro` both depend on `src/config/consent.config.ts`. If you change consent categories, storage keys, or consent mode, update the shared config instead of one component only.
- Blog routing assumes locale-prefixed content IDs and strips `fr/` from URLs when generating public blog paths, RSS links, and related-post links. Keep that normalization consistent if content files are added or locale handling changes.
- Default OG images are generated dynamically. If you add a new top-level static page that should get a generated `/og/...png`, update `src/pages/og/[...slug].png.ts` rather than only changing SEO metadata.
