#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from bitcointx import select_chain_params, set_custom_secp256k1_path
from bitcointx.core import b2x
from bitcointx.core.script import (
    CScript,
    OP_2,
    OP_3,
    OP_CHECKMULTISIG,
)
from bitcointx.wallet import CCoinKey, P2WSHBitcoinSignetAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str, str]:
    print("=== python-bitcointx: 2-of-3 P2WSH multisig address creator (Signet) ===\n")

    wif1 = input("Signer A private key (WIF, signet): ").strip()
    wif2 = input("Signer B private key (WIF, signet): ").strip()
    wif3 = input("Signer C private key (WIF, signet): ").strip()

    if not (wif1 and wif2 and wif3):
        raise ValueError("All three WIFs are required.")

    return wif1, wif2, wif3


def build_2of3_p2wsh_address(wif1: str, wif2: str, wif3: str) -> tuple[str, str]:
    key1 = CCoinKey(wif1)
    key2 = CCoinKey(wif2)
    key3 = CCoinKey(wif3)

    pubkeys = [key1.pub, key2.pub, key3.pub]

    print("\n[Debug] Signer pubkeys (compressed expected):")
    print(f"  A pubkey: {pubkeys[0].hex()}")
    print(f"  B pubkey: {pubkeys[1].hex()}")
    print(f"  C pubkey: {pubkeys[2].hex()}")

    # 2-of-3 multisig witnessScript: OP_2 <pub1> <pub2> <pub3> OP_3 OP_CHECKMULTISIG
    witness_script = CScript([OP_2, pubkeys[0], pubkeys[1], pubkeys[2], OP_3, OP_CHECKMULTISIG])

    print("\n[Debug] 2-of-3 multisig witnessScript:")
    print(f"  witnessScript (asm-like): OP_2 pubA pubB pubC OP_3 OP_CHECKMULTISIG")
    print(f"  witnessScript (hex)     : {b2x(witness_script)}")

    # Derive the native SegWit P2WSH address on Signet from the witnessScript
    p2wsh_address = P2WSHBitcoinSignetAddress.from_redeemScript(witness_script)

    print("\n[Debug] P2WSH scriptPubKey (hex):")
    print(f"  scriptPubKey: {p2wsh_address.to_scriptPubKey().hex()}")

    return str(p2wsh_address), b2x(witness_script)


def main() -> None:
    try:
        wif1, wif2, wif3 = read_inputs()
        address, witness_script_hex = build_2of3_p2wsh_address(wif1, wif2, wif3)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    print("\n=== 2-of-3 P2WSH multisig address (Signet) ===")
    print(f"P2WSH address        : {address}")
    print(f"witnessScript (hex)  : {witness_script_hex}")

    print("\nYou can use this P2WSH address as your Treasury address on Signet.")
    print("When spending this UTXO, you will need:")
    print("  - This witnessScript hex")
    print("  - At least 2 of the 3 corresponding WIFs to sign the PSBT")


if __name__ == "__main__":
    main()
