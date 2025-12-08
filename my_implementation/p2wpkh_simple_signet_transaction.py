#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from bitcointx import select_chain_params, set_custom_secp256k1_path
from bitcointx.core import (
    b2x,
    b2lx,
    x,
    lx,
    COutPoint,
    CMutableTxIn,
    CMutableTxOut,
    CMutableTransaction,
    CTxWitness,
    CTxInWitness,
)
from bitcointx.core.script import (
    CScript,
    CScriptWitness,
    SignatureHash,
    SIGHASH_ALL,
    SIGVERSION_WITNESS_V0,
)
from bitcointx.core.scripteval import VerifyScript
from bitcointx.wallet import CCoinKey, P2PKHCoinAddress, P2WPKHCoinAddress, CCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str, int, int, int, str]:
    print("=== python-bitcointx: simple signet P2WPKH tx builder ===\n")

    wif = input("Private key (WIF, signet): ").strip()
    prev_txid_hex = input("Prev txid (hex, big-endian): ").strip()
    vout_str = input("Prev output index (vout): ").strip()
    utxo_value_str = input("Prev output value (sats): ").strip()
    fee_str = input("Fee (sats): ").strip()
    dest_address = input("Destination address (signet, P2PKH or P2WPKH): ").strip()

    if not (wif and prev_txid_hex and vout_str and utxo_value_str and fee_str and dest_address):
        raise ValueError("All fields are required.")

    vout = int(vout_str)
    utxo_value = int(utxo_value_str)
    fee = int(fee_str)

    if utxo_value <= 0:
        raise ValueError("UTXO value must be positive")
    if fee <= 0:
        raise ValueError("Fee must be positive")
    if utxo_value <= fee:
        raise ValueError("UTXO value must be greater than fee")

    return wif, prev_txid_hex, vout, utxo_value, fee, dest_address


def build_and_sign_tx(
    wif: str,
    prev_txid_hex: str,
    vout: int,
    utxo_value: int,
    fee: int,
    dest_address: str,
) -> CMutableTransaction:
    send_value = utxo_value - fee

    key = CCoinKey(wif)

    prev_txid_bytes = lx(prev_txid_hex)
    txin = CMutableTxIn(COutPoint(prev_txid_bytes, vout))

    # For P2WPKH, the UTXO's scriptPubKey is the witness program
    #   OP_0 <20-byte-hash160(pubkey)>
    # but the scriptCode used for SignatureHash is the corresponding
    # P2PKH-style script:
    #   OP_DUP OP_HASH160 <hash160(pubkey)> OP_EQUALVERIFY OP_CHECKSIG
    witness_program_spk = P2WPKHCoinAddress.from_pubkey(key.pub).to_scriptPubKey()
    script_code = P2PKHCoinAddress.from_pubkey(key.pub).to_scriptPubKey()

    # Debug: show script/code and pubkey details to help diagnose
    print("\n[Debug] P2WPKH input details:")
    print(f"  pubkey         : {key.pub.hex()}")
    print(f"  script_code    : {script_code.hex()}  (P2PKH-style)")
    print(f"  witness prog SPK: {witness_program_spk.hex()}  (OP_0 <20-byte-hash160>)")

    txout = CMutableTxOut(
        send_value,
        CCoinAddress(dest_address).to_scriptPubKey(),
    )

    tx = CMutableTransaction([txin], [txout])

    sighash = SignatureHash(
        script_code,
        tx,
        0,
        SIGHASH_ALL,
        amount=utxo_value,
        sigversion=SIGVERSION_WITNESS_V0,
    )

    sig = key.sign(sighash) + bytes([SIGHASH_ALL])
    txin.scriptSig = CScript([])
    witness = CScriptWitness([sig, key.pub])
    tx.wit = CTxWitness([CTxInWitness(witness)])

    # Verify against the actual witness program scriptPubKey, explicitly
    # passing amount and witness data.
    VerifyScript(
        txin.scriptSig,
        witness_program_spk,
        tx,
        0,
        amount=utxo_value,
        witness=witness,
    )

    return tx


def main() -> None:
    try:
        wif, prev_txid_hex, vout, utxo_value, fee, dest_address = read_inputs()
        tx = build_and_sign_tx(wif, prev_txid_hex, vout, utxo_value, fee, dest_address)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    raw_hex = b2x(tx.serialize())
    txid = b2lx(tx.GetTxid())

    print("\n=== Signed transaction ===")
    print(f"TxID      : {txid}")
    print(f"Raw (hex) : {raw_hex}")

    print("\nYou can broadcast this transaction by:")
    print("  - Using your own signet node: bitcoin-cli -signet sendrawtransaction '<rawhex>'")
    print("  - Or via a block explorer that supports signet (paste the raw hex)")


if __name__ == "__main__":
    main()
