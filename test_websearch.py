#!/usr/bin/env python3
"""Test web search sur les modeles agentiques."""
import json, time, requests

URL = "http://localhost:8765/chat/completions"

MODELS = [
    (64, "gpt-5.6-sol", "openai"),
    (63, "claude-sonnet-5", "anthropic"),
    (100, "claude-opus-4-8", "anthropic"),
    (51, "claude-haiku-4-5", "anthropic"),
    (66, "gpt-5.6-terra", "openai"),
    (101, "gpt-5.5", "openai"),
]

QUERY = "Recherche le cours actuel du Bitcoin en dollars et le changement sur 24h. Reponds en 1 phrase."

for mid, mname, mprov in MODELS:
    print(f"\n{'='*80}")
    print(f"[{mid}] {mname} ({mprov})")
    print('='*80)
    
    try:
        resp = requests.post(URL, json={
            "message": QUERY,
            "model": mname,
            "enableWebSearch": True,
            "stream": False,
        }, timeout=60)
        
        data = resp.json()
        c = data.get("content", {})
        ws = c.get("webSearchCalls", [])
        text = c.get("text", "")
        tok = data.get("tokenUsage", {})
        
        print(f"  Web calls: {len(ws)}")
        for w in ws:
            print(f"    Query: {w.get('query', '?')}")
        print(f"  Tokens: {tok.get('totalTokenCount', '?')}")
        print(f"  Reponse: {text[:300]}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
    
    time.sleep(2)
