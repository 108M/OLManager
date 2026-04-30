# Changelog

All notable changes to OLManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses GPL-3.0 licensing inherited from the OpenFootManager lineage unless otherwise documented.

## [0.2.1] - 2026-04-30

### Fixed

- CI `generate-latest-json` job now checks out the repo so `gh release upload` has the correct repository context.

## [0.2.0] - 2026-04-30

### Added

- Stable auto-updater with signed releases and static JSON manifest.

## [0.1.9] - 2026-04-30

### Fixed

- CI artifact pattern typo corrected so `latest.json` generation can find `platform-info.json`.

## [0.1.8] - 2026-04-30

### Added

- Second end-to-end updater test with static JSON manifest.

## [0.1.7] - 2026-04-30

### Fixed

- Auto-updater now uses static JSON endpoint with properly generated `latest.json` and `.sig` signatures.

## [0.1.6] - 2026-04-30

### Added

- Minor UI tweak to verify end-to-end auto-updater detection.

## [0.1.5] - 2026-04-30

### Fixed

- Added `bundle.createUpdaterArtifacts: true` to `tauri.conf.json` so Tauri generates `.sig` signature files during the build.
- Added `updater:default` permission to `capabilities/default.json` so the frontend can call updater APIs.

## [0.1.4] - 2026-04-30

### Fixed

- Added `repository` field to `Cargo.toml` so `tauri-plugin-updater` can correctly resolve GitHub Releases API.

## [0.1.3] - 2026-04-30

### Added

- Test release for auto-updater verification.

## [0.1.2] - 2026-04-30

### Added

- Integrated `tauri-plugin-updater` for automatic updates via GitHub Releases.
- Added update check on app startup with modal prompt to install or dismiss.
- Added manual "Check for Updates" button in Settings.
- Added Ed25519 bundle signing for update verification.
- Added updater-related translations across all 7 supported languages.

### Changed

- Release workflow now signs bundles with `TAURI_SIGNING_PRIVATE_KEY` and uploads `.sig` files.
- `SIGNING_STATUS.txt` updated to reflect updater-level signing policy.

## [0.1.1] - 2026-04-28

### Added

- Added quality-of-life improvements to champion draft, including faster draft skipping, better role ordering, and champion sorting/filtering by meta and mastery.
- Added spectator/delegated match flow improvements so AI-controlled drafts and simulations can progress more smoothly through series games.

### Changed

- Improved match simulation and draft-result handling for series play, including safer handling of persisted draft results between games.
- Improved translations and UI labels across player, squad, champions, academy, and localized text.
- Removed duplicated draft players and the unavailable Omon free-agent entry from draft data.

### Fixed

- Fixed season-end progression issues and added coverage for end-of-season behavior.
- Fixed repeated press-conference questions by rotating recent questions and selecting a more varied question set.
- Fixed transfer messages to display match names instead of full names.
- Fixed the continue menu dropdown overlapping other UI elements.
- Disabled the native browser context menu in the Tauri app so the desktop experience behaves consistently.
- Fixed multiple transfer, potential, live-match, and match-simulation edge cases.

### Contributors

- Thanks to @drumst0ck (Jose Sánchez) for the transfer-message, continue-menu z-index, and Tauri context-menu fixes.

### Notes

- Release artifacts remain source-first; signing, notarization, and binary packaging policy are still not finalized.

## [0.1.0]

### Added

- Live Game simulation
- Customizable draft
- Player trading
- Installation management
- Functional Academy
- Training plans
- Scouting
- FULLY PLAYABLE (maybe not for long plays, but playable)
- Post-Game Press Conference
- Champion Mastery
- Live Patch/Meta changes
- Repository governance docs, issue templates, PR template, and non-production CI workflow for public OSS preparation.
- Provenance guidance separating GPL-inherited code/assets from third-party datasets and generated caches.
- Inherited documentation audit checklist for deciding which original-repository docs to keep, update, move to legacy, or remove before public OSS release.

### Notes

- Release artifacts are source-first until maintainers decide signing, notarization, and binary packaging policy.
