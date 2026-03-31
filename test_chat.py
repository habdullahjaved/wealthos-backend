# test_chat.py
import httpx

with httpx.stream(
    "POST",
    "http://localhost:8000/chat",
    json={"messages": [{"role": "user", "content": "Hello"}], "context": None},
    timeout=30,
) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                print("\n✅ Stream complete")
                break
            import json
            chunk = json.loads(payload)
            if "content" in chunk:
                print(chunk["content"], end="", flush=True)
            elif "error" in chunk:
                print(f"\n❌ Error: {chunk['error']}")