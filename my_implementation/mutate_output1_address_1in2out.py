#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from bitcointx import select_chain_params, set_custom_secp256k1_path
from bitcointx.core import (
    b2x,
    b2lx,
    CMutableTransaction,
)
from bitcointx.wallet import CCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str]:
    print("=== python-bitcointx: mutate output#1 address for 1-in-2-out tx ===\n")

    raw_hex = input("Raw transaction hex (1-in-2-out P2WPKH): ").strip()
    new_addr = input("New destination address for output #1: ").strip()

    if not (raw_hex and new_addr):
        raise ValueError("Both raw hex and new address are required.")

    return raw_hex, new_addr


def mutate_output1_address(raw_hex: str, new_addr: str) -> tuple[CMutableTransaction, int]:
    tx = CMutableTransaction.deserialize(bytes.fromhex(raw_hex))

    if len(tx.vin) != 1:
        raise ValueError("Transaction must have exactly 1 input (got %d)" % len(tx.vin))
    if len(tx.vout) != 2:
        raise ValueError("Transaction must have exactly 2 outputs (got %d)" % len(tx.vout))

    orig_value1 = tx.vout[1].nValue

    # Only replace scriptPubKey (address) of output #1, keep amount identical
    tx.vout[1].scriptPubKey = CCoinAddress(new_addr).to_scriptPubKey()

    return tx, orig_value1


def main() -> None:
    try:
        raw_hex, new_addr = read_inputs()
        tx_mut, orig_value1 = mutate_output1_address(raw_hex, new_addr)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    mutated_hex = b2x(tx_mut.serialize())
    txid = b2lx(tx_mut.GetTxid())

    print("\n[Result]")
    print(f"  Output #1 value (unchanged): {orig_value1} sats")
    print(f"  New TxID      : {txid}")
    print(f"  New Raw (hex) : {mutated_hex}")

    print("\nYou can now broadcast the mutated transaction by:")
    print("  - bitcoin-cli -signet sendrawtransaction '<new_rawhex>'")
    print("  - or a signet block explorer that accepts raw hex")
    print("Note: Whether it is accepted depends on the original SIGHASH type.")


if __name__ == "__main__":
    main()
