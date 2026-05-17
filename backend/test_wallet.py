import os
import sys
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import ed25519

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environmental variables from .env explicitly
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

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

def get_solana_wallet_address() -> str:
    """Derives the Solana wallet address (PublicKey) from the private key seed."""
    priv_key_b58 = os.getenv("SOLANA_PRIVATE_KEY")
    if not priv_key_b58:
        return "ERROR: Private key not found in .env"
        
    try:
        raw_bytes = base58_decode(priv_key_b58)
        # Solana private keys are usually 64 bytes (32-byte seed + 32-byte public key)
        private_seed = raw_bytes[:32]
        
        # Load key and derive public bytes
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_seed)
        pub_key_bytes = priv_key.public_key().public_bytes_raw()
        
        # Encode public bytes back to base58 to get wallet address
        wallet_address = base58_encode(pub_key_bytes)
        return wallet_address
    except Exception as e:
        return f"ERROR: Derivation failed ({str(e)})"

if __name__ == "__main__":
    print("=" * 80)
    print("🔑 DEX PREDATOR - WALLET INTEGRATION DIAGNOSTICS")
    print("=" * 80)
    print("[1/2] Loading wallet private key and running cryptographic derivation...", flush=True)
    
    address = get_solana_wallet_address()
    
    print("-" * 80)
    print(f"✅ DERIVASI SELESAI!")
    print(f"👉 Dompet Phantom Wallet Address Anda:")
    print(f"   ✨ \033[92m{address}\033[0m ✨")
    print("-" * 80)
    print("💡 Penjelasan Teknis:")
    print("  1. Kunci privat didekode dari format Base58.")
    print("  2. Seed kriptografis 32-byte pertama diekstrak.")
    print("  3. Alamat dompet publik dihitung menggunakan kurva Ed25519 native Python.")
    print("  4. Ini 100% aman karena berjalan di memori lokal server Anda tanpa pengiriman data.")
    print("=" * 80)
