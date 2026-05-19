const fs = require('fs');
const path = require('path');
const { Connection, Keypair, VersionedTransaction } = require('@solana/web3.js');
const bs58 = require('bs58').default || require('bs58');

// Load environment variables from absolute parent path .env
require('dotenv').config({ path: path.resolve(__dirname, '..', '.env') });

async function runSwap() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log(JSON.stringify({
            status: "error",
            message: "Usage: node onchain_executor.js <inputMint> <outputMint> <amountLamports> [slippageBps] [jitoTipLamports]"
        }));
        process.exit(1);
    }

    const inputMint = args[0];
    const outputMint = args[1];
    const amountLamports = parseInt(args[2]) || 10000000; // default 0.01 SOL
    const slippageBps = parseInt(args[3]) || 250; // default 2.5%
    const jitoTipLamports = parseInt(args[4]) || 1000000; // default 0.001 SOL

    const solPrivateKey = process.env.SOLANA_PRIVATE_KEY;
    const heliusUrl = process.env.SOLANA_RPC_HELIUS;
    const drpcUrl = process.env.SOLANA_RPC_DRPC;
    const jupApiKey = process.env.JUPITER_API_KEY;

    if (!solPrivateKey) {
        console.log(JSON.stringify({ status: "error", message: "Private key missing in .env" }));
        process.exit(1);
    }

    const SOL_MINT = "So11111111111111111111111111111111111111112";
    const inMint = inputMint.toLowerCase() === 'sol' ? SOL_MINT : inputMint;
    const outMint = outputMint.toLowerCase() === 'sol' ? SOL_MINT : outputMint;

    // Initialize keypair
    let keypair;
    try {
        const decodedSecret = bs58.decode(solPrivateKey);
        keypair = Keypair.fromSecretKey(decodedSecret);
    } catch (e) {
        console.log(JSON.stringify({ status: "error", message: `Failed to decode private key: ${e.message}` }));
        process.exit(1);
    }

    const headers = { "Content-Type": "application/json" };
    if (jupApiKey) {
        headers["x-api-key"] = jupApiKey;
    }

    // ------------------------------------------------------------------------
    //  STEP 1: FETCH ROUTING QUOTE (JUPITER SWAP V1 API)
    // ------------------------------------------------------------------------
    let quoteResponse;
    try {
        const quoteUrl = `https://api.jup.ag/swap/v1/quote?inputMint=${inMint}&outputMint=${outMint}&amount=${amountLamports}&slippageBps=${slippageBps}`;
        const quoteRes = await fetch(quoteUrl, { headers });
        if (!quoteRes.ok) {
            const errText = await quoteRes.text();
            throw new Error(`Jupiter V1 Quote Failed (${quoteRes.status}): ${errText}`);
        }
        quoteResponse = await quoteRes.json();
    } catch (e) {
        console.log(JSON.stringify({ status: "error", message: `Quote stage: ${e.message}` }));
        process.exit(1);
    }

    // ------------------------------------------------------------------------
    //  STEP 2: REQUEST SERIALIZED TRANSACTION (JUPITER SWAP V1 API)
    // ------------------------------------------------------------------------
    let swapTransaction;
    try {
        const swapPayload = {
            quoteResponse,
            userPublicKey: keypair.publicKey.toBase58(),
            wrapAndUnwrapSol: true,
            prioritizationFeeLamports: {
                jitoTipLamports
            },
            dynamicComputeUnitLimit: true
        };

        const swapRes = await fetch("https://api.jup.ag/swap/v1/swap", {
            method: "POST",
            headers,
            body: JSON.stringify(swapPayload)
        });

        if (!swapRes.ok) {
            const errText = await swapRes.text();
            throw new Error(`Jupiter V1 Swap Failed (${swapRes.status}): ${errText}`);
        }

        const swapData = await swapRes.json();
        swapTransaction = swapData.swapTransaction;
    } catch (e) {
        console.log(JSON.stringify({ status: "error", message: `Swap stage: ${e.message}` }));
        process.exit(1);
    }

    if (!swapTransaction) {
        console.log(JSON.stringify({ status: "error", message: "No swapTransaction returned by Jupiter V1" }));
        process.exit(1);
    }

    // ------------------------------------------------------------------------
    //  STEP 3: DESERIALIZE & SIGN VERSIONED TRANSACTION (NATIVE bindings)
    // ------------------------------------------------------------------------
    let tx;
    try {
        const swapTxBuf = Buffer.from(swapTransaction, 'base64');
        tx = VersionedTransaction.deserialize(swapTxBuf);
        tx.sign([keypair]);
    } catch (e) {
        console.log(JSON.stringify({ status: "error", message: `Signing stage: ${e.message}` }));
        process.exit(1);
    }

    // ------------------------------------------------------------------------
    //  STEP 4: PARALLEL RPC BROADCAST (HELIUS SENDER + dRPC)
    // ------------------------------------------------------------------------
    const serializedTx = tx.serialize();
    const rawTxBase64 = Buffer.from(serializedTx).toString('base64');

    const payload = {
        jsonrpc: "2.0",
        id: 1,
        method: "sendTransaction",
        params: [
            rawTxBase64,
            {
                encoding: "base64",
                skipPreflight: true,
                maxRetries: 2
            }
        ]
    };

    const signatures = [];
    const errors = [];

    // Broadcast in parallel
    const broadcastPromises = [];
    const heliusKey = process.env.HELIUS_API_KEY;

    if (heliusKey) {
        const senderUrl = `https://sender.helius-rpc.com/?api-key=${heliusKey}`;
        broadcastPromises.push(
            fetch(senderUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(json => {
                if (json.result) signatures.push(json.result);
                else errors.push(`Helius Sender Error: ${JSON.stringify(json.error)}`);
            })
            .catch(e => errors.push(`Helius Sender connection error: ${e.message}`))
        );
    } else if (heliusUrl) {
        broadcastPromises.push(
            fetch(heliusUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(json => {
                if (json.result) signatures.push(json.result);
                else errors.push(`Helius RPC Error: ${JSON.stringify(json.error)}`);
            })
            .catch(e => errors.push(`Helius connection error: ${e.message}`))
        );
    }

    if (drpcUrl) {
        broadcastPromises.push(
            fetch(drpcUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(json => {
                if (json.result) signatures.push(json.result);
                else errors.push(`dRPC RPC Error: ${JSON.stringify(json.error)}`);
            })
            .catch(e => errors.push(`dRPC connection error: ${e.message}`))
        );
    }

    if (jupApiKey) {
        const executePayload = {
            transaction: rawTxBase64
        };
        broadcastPromises.push(
            fetch("https://api.jup.ag/swap/v1/execute", {
                method: "POST",
                headers,
                body: JSON.stringify(executePayload)
            })
            .then(res => res.json())
            .then(json => {
                const txid = json.signature || json.txid;
                if (txid) signatures.push(txid);
                else errors.push(`Jupiter Execute Error: ${JSON.stringify(json)}`);
            })
            .catch(e => errors.push(`Jupiter Execute connection error: ${e.message}`))
        );
    }

    await Promise.all(broadcastPromises);

    if (signatures.length === 0) {
        console.log(JSON.stringify({
            status: "error",
            message: "Broadcast failed to all RPC nodes",
            details: errors
        }));
        process.exit(1);
    }

    const primarySig = signatures[0];
    console.log(JSON.stringify({
        status: "success",
        signature: primarySig,
        explorer_url: `https://solscan.io/tx/${primarySig}`,
        net_out_amount: quoteResponse.outAmount,
        price_impact_pct: parseFloat(quoteResponse.priceImpactPct || 0) * 100
    }, null, 2));
}

runSwap();
