# CLAUDE.md

This file provides project context for agents working with this repository.

## Project overview

「買い物リマインダー」— 定期的に購入するものの消費速度と現在の在庫を登録しておき、消費しきる前に「何を」「どれくらい」買うべきかを通知するアプリ。詳細な要件・データモデル・本番インフラ構成は README.md を参照。

## Repository layout

- `backend/` — FastAPI + boto3 (DynamoDB) API
- `frontend/` — React + TypeScript + Vite, bun管理
- `e2e/` — Playwright によるフルスタックE2Eテスト

## Current state

着手前に実際のファイル、既存テスト、CI結果を確認し、この記述よりコードを優先して現在地を判断すること。

## Evaluation branch

This branch is reserved for evaluating an unmodified installation of Superpowers. Do not restore or invoke the repository-specific development-cycle Skills, TDD orchestration, gate protocol, or four-agent workflow that exist on other branches. Use the installed vanilla Superpowers workflow without repository-specific workflow overrides.

Product code, existing tests, product requirements, architecture information, and ordinary repository configuration remain valid project context.
