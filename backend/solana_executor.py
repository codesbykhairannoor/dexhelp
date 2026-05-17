import os
import sys
import base64
import requests
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import ed25519

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environmental variables from absolute path .env
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

# ============================================================================-
#  BASE58 & CRYPTO UTILITIES
# ============================================================================-
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def base58_decode(b58_str: str) -> bytes:
    """Decodes a base58 encoded string to bytes."""
    num = 0
    for char in b58_str:
        num = num * 58 + BASE58_ALPHABET.index(char)
    combined = []
    while num > 0:
        num, mod = divmod(num, 256)
        combined.append(mod)
    pad = 0
    for char in b58_str:
        if char == '1':
            pad += 1
        else:
            break
    return bytes([0] * pad + list(reversed(combined)))

def base58_encode(b_arr: bytes) -> str:
    """Encodes bytes to a base58 string."""
    num = 0
    for byte in b_arr:
        num = num * 256 + byte
    b58_str = ""
    while num > 0:
        num, mod = divmod(num, 58)
        b58_str = BASE58_ALPHABET[mod] + b58_str
    pad = 0
    for byte in b_arr:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + b58_str

# ============================================================================-
#  SOLANA VERSIONED TRANSACTION SIGNER
# ============================================================================-

def sign_versioned_transaction(serialized_tx_base64: str, priv_key_b58: str) -> str:
    """
    Decodes, parses, cryptographically signs, and re-encodes a Solana VersionedTransaction.
    Uses native Ed25519 curves to replace the fee payer signature.
    """
    # 1. Decode transaction and private key seed
    tx_bytes = bytearray(base64.b64decode(serialized_tx_base64))
    raw_key = base58_decode(priv_key_b58)
    private_seed = raw_key[:32]
    
    # 2. Parse Compact-u16 Signature Count
    first_byte = tx_bytes[0]
    if first_byte < 128:
        num_signatures = first_byte
        offset = 1
    else:
        num_signatures = first_byte & 0x7f
        num_signatures |= (tx_bytes[1] << 7)
        offset = 2
        
    signatures_size = num_signatures * 64
    message_offset = offset + signatures_size
    message_bytes = tx_bytes[message_offset:]
    
    # 3. Sign Message Bytes using Native Ed25519
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_seed)
    signature = priv_key.sign(bytes(message_bytes))
    
    # 4. Overwrite fee payer signature (first signature slot, at index 'offset')
    tx_bytes[offset : offset + 64] = signature
    
    # 5. Return signed transaction as Base64 string
    return base64.b64encode(tx_bytes).decode('utf-8')

# ============================================================================-
#  DYNAMIC PRIORITY FEE ESTIMATOR (CONGESTION SHIELD)
# ============================================================================-

def get_dynamic_priority_fee(rpc_url: str, mint_address: str) -> int:
    """
    Queries Solana RPC getRecentPrioritizationFees for the target mint
    to calculate a high-percentile dynamic priority fee (in micro-lamports).
    """
    if not rpc_url:
        return 150000 # Fallback: 150k micro-lamports
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getRecentPrioritizationFees",
            "params": [[mint_address]]
        }
        res = requests.post(rpc_url, json=payload, timeout=5).json()
        fees = res.get("result", [])
        if not fees:
            return 150000
        # Sort by slot descending and take the 75th percentile fee of recent slots
        fees.sort(key=lambda x: x.get("slot", 0), reverse=True)
        recent_fees = [f.get("prioritizationFee", 0) for f in fees[:20]]
        recent_fees.sort()
        idx = int(len(recent_fees) * 0.75)
        optimal_fee = recent_fees[idx] if recent_fees else 150000
        return max(50000, min(1500000, optimal_fee)) # Cap between 50k and 1.5m micro-lamports
    except Exception:
        return 150000

# ============================================================================-
#  JUPITER SWAP EXECUTION ENGINE
# ============================================================================-

def execute_solana_swap(
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = 250,
    jito_tip_lamports: int = 1000000
) -> dict:
    """
    Performs an automated end-to-end token swap on Solana using Jupiter and Helius/dRPC.
    1. Fetches Routing Quote from Jupiter Quote API.
    2. Requests Serialized Transaction from Jupiter Swap API.
    3. Signs transaction cryptographically with local Ed25519 engine.
    4. Broadcasts Raw Signed Transaction in parallel to Helius and dRPC.
    """
    jup_api_key = os.getenv("JUPITER_API_KEY")
    priv_key_b58 = os.getenv("SOLANA_PRIVATE_KEY")
    helius_url = os.getenv("SOLANA_RPC_HELIUS")
    drpc_url = os.getenv("SOLANA_RPC_DRPC")
    
    if not priv_key_b58:
        return {"status": "error", "message": "Private key missing in .env"}
        
    # Standard SOL wrapper mint
    SOL_MINT = "So11111111111111111111111111111111111111112"
    in_mint = SOL_MINT if input_mint.lower() == "sol" else input_mint
    out_mint = SOL_MINT if output_mint.lower() == "sol" else output_mint
    
    headers = {
        "x-api-key": jup_api_key,
        "Content-Type": "application/json"
    } if jup_api_key else {"Content-Type": "application/json"}
    
    # ------------------------------------------------------------------------
    #  STEP 1: FETCH ROUTING QUOTE
    # ------------------------------------------------------------------------
    try:
        quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint={in_mint}&outputMint={out_mint}&amount={amount_lamports}&slippageBps={slippage_bps}"
        r = requests.get(quote_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"status": "error", "message": f"Jupiter Quote failed (Code:{r.status_code}): {r.text}"}
        quote_res = r.json()
    except Exception as e:
        return {"status": "error", "message": f"Jupiter Quote call failed: {str(e)}"}
        
    # Derive derived wallet address for execution tracking
    raw_key = base58_decode(priv_key_b58)
    user_wallet = base58_encode(raw_key[32:])
    
    # ------------------------------------------------------------------------
    #  STEP 2: REQUEST SERIALIZED TRANSACTION (WITH DYNAMIC PRIORITY FEES)
    # ------------------------------------------------------------------------
    try:
        # Calculate dynamic prioritization fee based on current network congestion
        dynamic_priority_fee = get_dynamic_priority_fee(helius_url or drpc_url, out_mint)
        
        swap_payload = {
            "quoteResponse": quote_res,
            "userPublicKey": user_wallet,
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": {
                "jitoTipLamports": jito_tip_lamports
            },
            # Allow Jupiter auto-priority calculation as a fallback safety
            "dynamicComputeUnitLimit": True
        }
        
        r = requests.post("https://api.jup.ag/swap/v1/swap", headers=headers, json=swap_payload, timeout=10)
        if r.status_code != 200:
            return {"status": "error", "message": f"Jupiter Swap Payload failed (Code:{r.status_code}): {r.text}"}
        swap_res = r.json()
        serialized_tx = swap_res.get("swapTransaction")
    except Exception as e:
        return {"status": "error", "message": f"Jupiter Swap call failed: {str(e)}"}
        
    if not serialized_tx:
        return {"status": "error", "message": "No swapTransaction returned by Jupiter API"}
        
    # ------------------------------------------------------------------------
    #  STEP 3: CRYPTOGRAPHICALLY SIGN TRANSACTION (LOCAL MEMORY)
    # ------------------------------------------------------------------------
    try:
        signed_tx_base64 = sign_versioned_transaction(serialized_tx, priv_key_b58)
    except Exception as e:
        return {"status": "error", "message": f"Local cryptographic signing failed: {str(e)}"}
        
    # ------------------------------------------------------------------------
    #  STEP 4: PARALLEL RPC BROADCAST (HELIUS + dRPC FOR ULTRAPORT CONFIRMATION)
    # ------------------------------------------------------------------------
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sendTransaction",
        "params": [
            signed_tx_base64,
            {
                "encoding": "base64",
                "skipPreflight": True,
                "maxRetries": 2
            }
        ]
    }
    
    broadcast_errors = []
    signatures = []
    
    # Broadcast to Helius
    if helius_url:
        try:
            res = requests.post(helius_url, json=rpc_payload, timeout=5).json()
            if "result" in res:
                signatures.append(res["result"])
            else:
                broadcast_errors.append(f"Helius RPC error: {res.get('error')}")
        except Exception as e:
            broadcast_errors.append(f"Helius broadcast failed: {str(e)}")
            
    # Broadcast to dRPC
    if drpc_url:
        try:
            res = requests.post(drpc_url, json=rpc_payload, timeout=5).json()
            if "result" in res:
                signatures.append(res["result"])
            else:
                broadcast_errors.append(f"dRPC RPC error: {res.get('error')}")
        except Exception as e:
            broadcast_errors.append(f"dRPC broadcast failed: {str(e)}")
            
    if not signatures:
        return {
            "status": "error",
            "message": "Broadcast failed to all RPC nodes",
            "details": broadcast_errors
        }
        
    # Take the first signature
    primary_sig = signatures[0]
    return {
        "status": "success",
        "signature": primary_sig,
        "explorer_url": f"https://solscan.io/tx/{primary_sig}",
        "net_out_amount": quote_res.get("outAmount"),
        "price_impact_pct": float(quote_res.get("priceImpactPct", 0)) * 100
    }

if __name__ == "__main__":
    # Self-test: Derive and print wallet
    priv = os.getenv("SOLANA_PRIVATE_KEY")
    if priv:
        raw = base58_decode(priv)
        wallet = base58_encode(raw[32:])
        print(f"[EXECUTOR] Native Solana Swap Engine Loaded. Target Wallet: {wallet}", flush=True)
