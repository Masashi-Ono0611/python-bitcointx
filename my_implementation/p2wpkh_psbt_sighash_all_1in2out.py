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
    CTxOut,
)
from bitcointx.core.psbt import PartiallySignedTransaction, PSBT_Input, PSBT_Output
from bitcointx.core.key import KeyStore
from bitcointx.core.script import (
    CScript,
    SIGHASH_ALL,
    SIGVERSION_WITNESS_V0,
    SignatureHash,
)
from bitcointx.wallet import CCoinKey, P2WPKHCoinAddress, CCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


class SingleKeyStore(KeyStore):
    def __init__(self, key: CCoinKey) -> None:
        super().__init__()
        self._key = key

    def get_privkey(self, key_id, derinfo=None):  # type: ignore[override]
        if self._key.pub.key_id == key_id:
            return self._key
        return None


def read_inputs() -> tuple[str, str, int, int, int, int, str, str]:
    print("=== python-bitcointx: P2WPKH PSBT SIGHASH_ALL 1-in-2-out demo ===\n")

    wif = input("Private key (WIF, signet): ").strip()
    prev_txid_hex = input("Prev txid (hex, big-endian): ").strip()
    vout_str = input("Prev output index (vout): ").strip()
    utxo_value_str = input("Prev output value (sats): ").strip()
    fee_str = input("Fee (sats): ").strip()
    commit_value_str = input("First output value (sats, output #0): ").strip()
    dest_address0 = input("Destination address for output #0: ").strip()
    dest_address1 = input("Destination address for output #1: ").strip()

    if not (
        wif
        and prev_txid_hex
        and vout_str
        and utxo_value_str
        and fee_str
        and commit_value_str
        and dest_address0
        and dest_address1
    ):
        raise ValueError("All fields are required.")

    vout = int(vout_str)
    utxo_value = int(utxo_value_str)
    fee = int(fee_str)
    value0 = int(commit_value_str)

    if utxo_value <= 0:
        raise ValueError("UTXO value must be positive")
    if fee <= 0:
        raise ValueError("Fee must be positive")
    if utxo_value <= fee:
        raise ValueError("UTXO value must be greater than fee")

    total_sendable = utxo_value - fee
    if value0 <= 0 or value0 >= total_sendable:
        raise ValueError("First output value must be > 0 and < (utxo_value - fee)")

    return (
        wif,
        prev_txid_hex,
        vout,
        utxo_value,
        fee,
        value0,
        dest_address0,
        dest_address1,
    )


def build_psbt_p2wpkh_sighash_all_1in2out(
    wif: str,
    prev_txid_hex: str,
    vout: int,
    utxo_value: int,
    fee: int,
    value0: int,
    dest_address0: str,
    dest_address1: str,
) -> PartiallySignedTransaction:
    total_sendable = utxo_value - fee
    value1 = total_sendable - value0

    key = CCoinKey(wif)

    prev_txid_bytes = lx(prev_txid_hex)
    txin = CMutableTxIn(COutPoint(prev_txid_bytes, vout))

    witness_program_spk = P2WPKHCoinAddress.from_pubkey(key.pub).to_scriptPubKey()
    script_code = P2WPKHCoinAddress.from_pubkey(key.pub).to_redeemScript()

    txout0 = CMutableTxOut(
        value0,
        CCoinAddress(dest_address0).to_scriptPubKey(),
    )

    txout1 = CMutableTxOut(
        value1,
        CCoinAddress(dest_address1).to_scriptPubKey(),
    )

    unsigned_tx = CMutableTransaction([txin], [txout0, txout1])

    witness_utxo = CTxOut(utxo_value, witness_program_spk)

    psbt_in = PSBT_Input(
        unsigned_tx=unsigned_tx,
        utxo=witness_utxo,
        index=0,
        sighash_type=int(SIGHASH_ALL),
    )

    psbt_out0 = PSBT_Output(index=0)
    psbt_out1 = PSBT_Output(index=1)

    psbt = PartiallySignedTransaction(
        unsigned_tx=unsigned_tx,
        inputs=[psbt_in],
        outputs=[psbt_out0, psbt_out1],
    )

    keystore = SingleKeyStore(key)

    sighash_all = SignatureHash(
        script_code,
        unsigned_tx,
        0,
        SIGHASH_ALL,
        amount=utxo_value,
        sigversion=SIGVERSION_WITNESS_V0,
    )

    print("\n[Debug] SIGHASH (1-in-2-out, SIGHASH_ALL):")
    print(f"  SIGHASH_ALL : {b2x(sighash_all)}")
    print("  (Note: ALL commits to both outputs #0 and #1.)")

    sig = key.sign(sighash_all) + bytes([int(SIGHASH_ALL)])

    psbt.inputs[0].final_script_sig = CScript([])
    from bitcointx.core.script import CScriptWitness  # local import to avoid top reordering

    psbt.inputs[0].final_script_witness = CScriptWitness([sig, key.pub])

    return psbt


def main() -> None:
    try:
        (
            wif,
            prev_txid_hex,
            vout,
            utxo_value,
            fee,
            value0,
            dest_address0,
            dest_address1,
        ) = read_inputs()
        psbt = build_psbt_p2wpkh_sighash_all_1in2out(
            wif,
            prev_txid_hex,
            vout,
            utxo_value,
            fee,
            value0,
            dest_address0,
            dest_address1,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    final_tx = psbt.extract_transaction()
    raw_hex = b2x(final_tx.serialize())
    txid = b2lx(final_tx.GetTxid())

    print("\n=== Signed transaction (PSBT, SIGHASH_ALL, 1-in-2-out) ===")
    print(f"TxID      : {txid}")
    print(f"Raw (hex) : {raw_hex}")

    print("\nYou can broadcast this transaction by:")
    print("  - Using your own signet node: bitcoin-cli -signet sendrawtransaction '<rawhex>'")
    print("  - Or via a block explorer that supports signet (paste the raw hex)")


if __name__ == "__main__":
    main()
