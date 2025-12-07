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
)
from bitcointx.core.script import CScript, SignatureHash, SIGHASH_ALL
from bitcointx.core.scripteval import VerifyScript
from bitcointx.wallet import CCoinKey, P2PKHCoinAddress, CCoinAddress


# Ensure we use the locally built secp256k1 v0.4.0
set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

# Always use signet for this demo
select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str, int, int, int, str]:
    print("=== python-bitcointx: simple signet P2PKH tx builder ===\n")

    wif = input("Private key (WIF, signet): ").strip()
    prev_txid_hex = input("Prev txid (hex, big-endian): ").strip()
    vout_str = input("Prev output index (vout): ").strip()
    utxo_value_str = input("Prev output value (sats): ").strip()
    fee_str = input("Fee (sats): ").strip()
    dest_address = input("Destination P2PKH address (signet): ").strip()

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

    # Input (outpoint)
    # User supplies txid as shown in explorers (big-endian hex),
    # so convert with x() rather than lx().
    prev_txid_bytes = lx(prev_txid_hex)
    txin = CMutableTxIn(COutPoint(prev_txid_bytes, vout))

    # scriptPubKey of the UTXO we are spending (P2PKH for our key)
    txin_script_pubkey = P2PKHCoinAddress.from_pubkey(key.pub).to_scriptPubKey()

    # Output to destination address (use CCoinAddress so that chain params
    # such as bitcoin/signet are respected)
    txout = CMutableTxOut(
        send_value,
        CCoinAddress(dest_address).to_scriptPubKey(),
    )

    tx = CMutableTransaction([txin], [txout])

    # Signature hash for input 0
    sighash = SignatureHash(txin_script_pubkey, tx, 0, SIGHASH_ALL)

    # Sign and attach scriptSig
    sig = key.sign(sighash) + bytes([SIGHASH_ALL])
    tx.vin[0].scriptSig = CScript([sig, key.pub])

    # Verify locally against the tx's actual input
    VerifyScript(tx.vin[0].scriptSig, txin_script_pubkey, tx, 0)

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
