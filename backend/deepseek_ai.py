import os, time, requests, json

def get_api_key():
    key = os.getenv("QWEN_API_KEY")
    if key: return key
    
    # Check backend/.env first
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'QWEN_API_KEY' in line and not line.startswith('#'):
                    val = line.split('=')[-1].strip().strip('"').strip("'")
                    if val: return val
                    
    # Check parent directory ../.env
    root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(root_env):
        with open(root_env, 'r') as f:
            for line in f:
                if 'QWEN_API_KEY' in line and not line.startswith('#'):
                    return line.split('=')[-1].strip().strip('"').strip("'")
    return None

def evaluate_token(symbol, name):
    api_key = get_api_key()
    if not api_key:
        return {"error": "No QWEN_API_KEY found"}
        
    start_time = time.time()
    
    prompt = f"""
Analyze the viral/memetic potential of this Solana token:
Symbol: {symbol}
Name: {name}

Output MUST be a raw JSON object with NO markdown wrappers or extra text.
Format: {{"score": <1-100 integer>, "reason": "<brief 1 sentence reason>"}}
- High score (>80): Viral meme formats (Dog, Pepe, Cat, Wif, Hats), cult-like, catchy.
- Low score (<30): Generic crypto words, random letters, boring, lazy AI names, obviously spam.
"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "qwen-turbo",
        "messages": [
            {"role": "system", "content": "You are a hyper-intelligent degen memecoin sniper algorithm."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "stream": False
    }
    
    try:
        r = requests.post("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions", headers=headers, json=payload, timeout=45)
        latency = time.time() - start_time
        
        if r.status_code == 200:
            res = r.json()
            message = res["choices"][0]["message"]
            content = message.get("content", "")
            
            try:
                parsed = json.loads(content)
                return {
                    "latency_sec": latency, 
                    "score": parsed.get("score", 0), 
                    "reason": parsed.get("reason", "")
                }
            except Exception as e:
                return {"latency_sec": latency, "error": f"Parse Error: {content}"}
        else:
            return {"latency_sec": latency, "error": f"API Error {r.status_code}: {r.text}"}
    except Exception as e:
        return {"latency_sec": time.time() - start_time, "error": str(e)}
