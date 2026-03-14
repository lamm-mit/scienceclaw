# Research Plan Summary

This document outlines a four-part implementation workflow for research projects. Here are the key components:

## Core Process

The research plan requires completing a "Novix Plan Agent" mechanism that transforms survey findings into actionable implementation steps. The workflow mandates: "Don't ask permission. Just do it."

## Four Required Sections

1. **Dataset Plan** — Specifies data source, preprocessing steps, and DataLoader configuration
2. **Model Plan** — Details architecture with component-to-formula mapping and reference code paths
3. **Training Plan** — Defines loss functions, optimizer settings, and monitoring metrics
4. **Testing Plan** — Establishes evaluation metrics, baselines, and ablation studies

## Critical Requirements

- Each model component must "have corresponding formula" and reference code from analyzed repositories
- Plans must include concrete parameter values, not generic recommendations
- Prerequisites include `task.json`, `survey_res.md`, and repository analysis
- Missing `survey_res.md` halts execution with message: "需要先运行 /research-survey 完成深度分析"

## Validation Checklist

The self-check ensures: components map to formulas, reference code is documented, datasets have acquisition methods, loss functions have mathematical definitions, and evaluation metrics are clearly specified.
