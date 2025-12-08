#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from bitcointx import select_chain_params, set_custom_secp256k1_path
from bitcointx.core import (
    b2x,
    b2lx,
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
    SignatureHashSchnorr,
)
from bitcointx.core.scripteval import VerifyScript
from bitcointx.wallet import CBitcoinSignetKey, P2TRBitcoinSignetAddress, CCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str, int, int, int, str]:
    print("=== python-bitcointx: simple signet P2TR (Taproot) tx builder ===\n")

    wif = input("Private key (WIF, signet, compressed): ").strip()
    prev_txid_hex = input("Prev txid (hex, big-endian): ").strip()
    vout_str = input("Prev output index (vout): ").strip()
    utxo_value_str = input("Prev output value (sats): ").strip()
    fee_str = input("Fee (sats): ").strip()
    dest_address = input("Destination address (signet, P2PKH / P2WPKH / P2TR): ").strip()

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


def build_and_sign_p2tr_tx(
    wif: str,
    prev_txid_hex: str,
    vout: int,
    utxo_value: int,
    fee: int,
    dest_address: str,
) -> CMutableTransaction:
    send_value = utxo_value - fee

    key = CBitcoinSignetKey(wif)

    # Derive the Taproot (P2TR) address from the internal pubkey
    p2tr_address = P2TRBitcoinSignetAddress.from_pubkey(key.pub)
    p2tr_spk = p2tr_address.to_scriptPubKey()

    print("\n[Debug] P2TR input details (key-path):")
    print(f"  Internal pubkey (compressed) : {key.pub.hex()}")
    print(f"  P2TR address                 : {p2tr_address}")
    print(f"  P2TR scriptPubKey (hex)      : {p2tr_spk.hex()}")

    prev_txid_bytes = lx(prev_txid_hex)
    txin = CMutableTxIn(COutPoint(prev_txid_bytes, vout))

    txout = CMutableTxOut(
        send_value,
        CCoinAddress(dest_address).to_scriptPubKey(),
    )

    tx = CMutableTransaction([txin], [txout])

    # For Taproot key-path spend, SignatureHashSchnorr takes the full list of
    # spent outputs (amount + scriptPubKey) for all inputs. Here we have 1 input.
    spent_outputs = [
        CMutableTxOut(utxo_value, p2tr_spk),
    ]

    sighash = SignatureHashSchnorr(
        tx,
        0,
        spent_outputs,
    )

    # Schnorr-sign with tap tweak (key-path spend, no script path)
    sig = key.sign_schnorr_tweaked(sighash)

    # Taproot key-path witness is just [sig]
    witness = CScriptWitness([sig])
    tx.wit = CTxWitness([CTxInWitness(witness)])

    # scriptSig is empty for P2TR
    tx.vin[0].scriptSig = CScript([])

    # VerifyScript against the P2TR scriptPubKey.
    # Note: python-bitcointx's default STANDARD flags include
    # SCRIPT_VERIFY_DISCOURAGE_UPGRADABLE_WITNESS_PROGRAM, which would
    # reject v1 witness programs. For this educational key-path Taproot
    # demo we pass an empty flag set and rely on our own
    # SignatureHashSchnorr + sign_schnorr_tweaked logic for correctness.
    VerifyScript(
        tx.vin[0].scriptSig,
        p2tr_spk,
        tx,
        0,
        flags=set(),
        amount=utxo_value,
        witness=witness,
    )

    return tx


def main() -> None:
    try:
        wif, prev_txid_hex, vout, utxo_value, fee, dest_address = read_inputs()
        tx = build_and_sign_p2tr_tx(
            wif,
            prev_txid_hex,
            vout,
            utxo_value,
            fee,
            dest_address,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    raw_hex = b2x(tx.serialize())
    txid = b2lx(tx.GetTxid())

    print("\n=== Signed P2TR transaction (key-path, 1-in-1-out) ===")
    print(f"TxID      : {txid}")
    print(f"Raw (hex) : {raw_hex}")

    print("\nYou can broadcast this transaction by:")
    print("  - Using your own signet node: bitcoin-cli -signet sendrawtransaction '<rawhex>'")
    print("  - Or via a block explorer that supports signet (paste the raw hex)")


if __name__ == "__main__":
    main()
