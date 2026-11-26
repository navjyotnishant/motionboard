<!--
Sync Impact Report
Version: 0.0.0 -> 1.0.0 (initial ratification)
Principles added: I to VII
Templates: plan-template.md Constitution Check gates should reference these principles (no edits needed yet)
-->

# Motionboard Constitution

Motionboard is an open source Claude plugin that turns a song and a storyboard into a finished music video on the creator's own machine.

## Core Principles

### I. Storyboard First (NON-NEGOTIABLE)
Every video starts from a storyboard: one shot per sung line or beat, each with an image plate, a single clear action, the camera move and the timing. No clip is generated until the creator approves the storyboard. Changing the story means changing the storyboard first, then regenerating only the affected shots.

### II. Local First, Free by Default
The default pipeline runs on the creator's own hardware with open weight models (LTX-2.3 today). Paid services are optional backends, never required. Any step that spends money or credits states the expected cost and waits for an explicit yes.

### III. Never Crash the Machine
Every heavy job runs under a memory and swap guard with configurable limits. Before a run, Motionboard checks whether the chosen model, resolution and frame count fit the machine (dry run fit check) and refuses or downsizes when they do not. A guard that stops a job reports why and what to change. Limits are a user setting with safe presets, never silently loosened.

### IV. No Bundled Weights, Respect Licenses
The plugin ships code, prompts and templates only. Creators download model weights from their source after accepting that model's license. Motionboard surfaces each model's license terms and output usage rules, and flags synthetic realistic people so the creator can label content correctly on each platform.

### V. Review Gates Between Stages
Four stages, each a separate command: setup check, storyboard, plates and clips, finish and deliver. Each stage ends with something the creator can look at (contact sheet, per shot preview, final cut) and does not move on without approval. Work is resumable: finished shots are never regenerated unless asked.

### VI. Honest Verification
Every stage reports what was checked and what was not. Sync claims rest on measured beats or timestamps, not assumptions. Failures are reported plainly with the next step, never hidden behind a partial success.

### VII. Simple and Portable
Project state lives in one local embedded database file; media stay as plain files on disk. Every project exports to and imports from readable JSON, so nothing is locked in. One project folder per video. Backends and image sources sit behind small adapters so new models (Wan, newer LTX) and providers can be added without touching the stages.

### VIII. One Source of Truth, Two Ways In
The chat commands and the Storyboard Studio web app read and write the same state. Anything the creator can do in one is visible in the other. Everything runs on the creator's machine on localhost; Motionboard is never a hosted website. Core editing, review and export work without internet or an account. The interface is a minimal, imagery first media tool: dark by default, frames and clips are the content, controls recede.

## Constraints

- Primary target: Apple Silicon Macs (MLX). Other platforms are welcome but secondary for v1.
- Output formats: 9:16 reels and 16:9 full videos, H.264 plus AAC.
- Secrets (API keys, tokens) are read from files or environment, never printed or committed.
- Commits carry no AI attribution lines.
- Licensing: engine, Studio and plugin glue are Apache License 2.0. Mode animation packs (`modes/*/animation/`) are Motionboard's IP and ship under PolyForm Noncommercial 1.0.0. Videos made with them belong to their creators.

## Development Workflow

Spec Kit drives the work: constitution, specify, clarify, plan, tasks, implement. Every feature names the principles it touches in its plan's Constitution Check. Real projects (starting with NAVAAN After Dark) are the acceptance tests.

## Governance

This constitution overrides other practice in the repo. Amendments are a pull request that updates this file, bumps the version (major for removed or redefined principles, minor for new ones, patch for wording) and notes the change in the Sync Impact Report.

**Version**: 1.2.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-24
