# Frontend App Splitting Plan

## Current Boundary

`frontend_pro/src/App.jsx` should move back toward an application shell that owns:

- global layout
- top-level navigation
- page switching
- cross-page shared state wiring

It should not continue absorbing long page implementations, report rendering details, or one-off helper logic.

## First Round Completed

The first round focuses on low-risk extraction without changing the overall page flow:

- move `PageHeader` out of `App.jsx`
- move `StatCard` out of `App.jsx`
- move `CategoryCard` out of `App.jsx`
- move `LogViewer` out of `App.jsx`
- move report display helpers and pagination/category formatting logic into `components/reports/reportUtils.js`

This reduces `App.jsx` size immediately while keeping current behavior stable.

## Next Round

The next safe split should target the report module first:

- extract the report list view into a report page component
- extract the report detail view into a dedicated page component
- extract report filter/sort state into a report hook
- extract history/task fetching into a service module

## Later Rounds

- split dashboard/home content from `App.jsx`
- split algorithm configuration page logic
- move shared formatting and request helpers into `utils/` and `services/`

## Guardrails

- prefer behavior-preserving moves before structural rewrites
- keep each extraction in a separately reviewable PR
- run the frontend build after every split step
