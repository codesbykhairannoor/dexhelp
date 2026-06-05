import os, time, requests, json

def get_api_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if key: return key
    
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if 'DEEPSEEK_API_KEY' in line:
                    return line.split('=')[-1].strip().strip('"').strip("'")
    return None

def evaluate_token(symbol, name):
    api_key = get_api_key()
    if not api_key:
        return {"error": "No API key found"}
        
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
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a hyper-intelligent degen memecoin sniper algorithm."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "stream": False
    }
    
    try:
        r = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=3)
        latency = time.time() - start_time
        
        if r.status_code == 200:
            res = r.json()
            content = res["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
                return {"latency_sec": latency, "score": parsed.get("score"), "reason": parsed.get("reason")}
            except Exception as e:
                return {"latency_sec": latency, "error": f"Parse Error: {content}"}
        else:
            return {"latency_sec": latency, "error": f"API Error {r.status_code}: {r.text}"}
    except Exception as e:
        return {"latency_sec": time.time() - start_time, "error": str(e)}

if __name__ == "__main__":
    tokens = [
        {"symbol": "WIF", "name": "dogwifhat"},
        {"symbol": "POPCAT", "name": "Popcat"},
        {"symbol": "TEST123A", "name": "TestToken123 Alpha"},
        {"symbol": "PEPE", "name": "Pepe"},
        {"symbol": "AIXGPT", "name": "AIXGPT Network Token"},
        {"symbol": "FUCK", "name": "FUCK JOE BIDEN"},
        {"symbol": "MOGGED", "name": "Mogged by Chad"}
    ]
    
    print("MEMULAI SUPER BACKTEST DEEPSEEK-V4-FLASH\n")
    print("Menganalisis 7 sampel token (Campuran Viral & Scam)...\n")
    print("-" * 80)
    for t in tokens:
        print(f"Mengaudit: {t['name']} ({t['symbol']})")
        res = evaluate_token(t['symbol'], t['name'])
        
        if "error" in res:
            print(f"  [GAGAL] Waktu: {res['latency_sec']:.2f}s | Error: {res['error']}")
        else:
            print(f"  [SUKSES] Waktu: {res['latency_sec']:.2f}s | Skor: {res['score']}/100")
            print(f"  [ALASAN] {res['reason']}")
        print("-" * 80)
