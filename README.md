# TDS-Project-1-LLM-Code_Deployment
# LLM Code Deployment - Starter

This project provides a FastAPI-based endpoint that accepts evaluation requests and uses a Large Language Model (LLM)
to generate a minimal web app from a provided brief, then pushes it to GitHub and enables GitHub Pages.

## Quickstart

1. Copy `.env` and fill in your real secrets (do NOT commit `.env` to git)
2. Install requirements: `pip install -r requirements.txt`
3. Run locally: `uvicorn main:app --reload`
4. Send a test POST to `/api-endpoint` as described in the project spec.

## Security notes
- Replace placeholder tokens in `.env` with real tokens locally.
- Never commit real API keys or tokens.
