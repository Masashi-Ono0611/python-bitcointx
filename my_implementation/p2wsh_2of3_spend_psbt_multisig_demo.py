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
from bitcointx.core.script import (
    CScript,
    CScriptWitness,
    SIGHASH_ALL,
    SIGVERSION_WITNESS_V0,
    SignatureHash,
)
from bitcointx.wallet import CCoinKey, CCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)

select_chain_params("bitcoin/signet")


def read_inputs() -> tuple[str, str, str, str, int, str, int]:
    print("=== python-bitcointx: 2-of-3 P2WSH PSBT multisig spend demo (Signet) ===\n")

    wif_a = input("Signer A private key (WIF, signet): ").strip()
    wif_b = input("Signer B private key (WIF, signet): ").strip()
    wif_c = input("Signer C private key (WIF, signet): ").strip()

    prev_txid_hex = input("Prev txid (hex, big-endian): ").strip()
    vout_str = input("Prev output index (vout): ").strip()
    utxo_value_str = input("Prev output value (sats): ").strip()

    witness_script_hex = input("2-of-3 witnessScript (hex): ").strip()

    dest_address = input("Destination address (signet, P2PKH / P2WPKH / P2WSH): ").strip()
    fee_str = input("Fee (sats): ").strip()

    if not (wif_a and wif_b and wif_c and prev_txid_hex and vout_str and utxo_value_str and witness_script_hex and dest_address and fee_str):
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

    return (
        wif_a,
        wif_b,
        wif_c,
        prev_txid_hex,
        vout,
        witness_script_hex,
        utxo_value,
        dest_address,
        fee,
    )


def build_unsigned_psbt_1in1out_p2wsh(
    wif_a: str,
    wif_b: str,
    wif_c: str,
    prev_txid_hex: str,
    vout: int,
    witness_script_hex: str,
    utxo_value: int,
    dest_address: str,
    fee: int,
) -> tuple[PartiallySignedTransaction, CScript, list[CCoinKey]]:
    key_a = CCoinKey(wif_a)
    key_b = CCoinKey(wif_b)
    key_c = CCoinKey(wif_c)
    keys = [key_a, key_b, key_c]

    witness_script = CScript(bytes.fromhex(witness_script_hex))

    print("\n[Debug] Loaded 2-of-3 witnessScript:")
    print(f"  witnessScript (hex): {witness_script_hex}")
    print("  Pubkeys found in witnessScript are expected to match A/B/C keys.")

    prev_txid_bytes = lx(prev_txid_hex)
    txin = CMutableTxIn(COutPoint(prev_txid_bytes, vout))

    send_value = utxo_value - fee

    txout = CMutableTxOut(
        send_value,
        CCoinAddress(dest_address).to_scriptPubKey(),
    )

    unsigned_tx = CMutableTransaction([txin], [txout])

    # P2WSH: the witness_utxo scriptPubKey is the P2WSH program (OP_0 <32-byte-hash>)
    # In this demo we rely on the fact that the UTXO we are spending is exactly this P2WSH.
    # The scriptPubKey is not reconstructed automatically from witness_script; we expect
    # that the user has funded the P2WSH address generated from the same witnessScript.
    from bitcointx.wallet import P2WSHBitcoinSignetAddress  # local import to avoid reordering

    p2wsh_address = P2WSHBitcoinSignetAddress.from_redeemScript(witness_script)
    witness_program_spk = p2wsh_address.to_scriptPubKey()

    print("\n[Debug] P2WSH UTXO details:")
    print(f"  P2WSH address     : {p2wsh_address}")
    print(f"  scriptPubKey (hex): {witness_program_spk.hex()}")
    print(f"  UTXO value (sats) : {utxo_value}")

    witness_utxo = CTxOut(utxo_value, witness_program_spk)

    psbt_in = PSBT_Input(
        unsigned_tx=unsigned_tx,
        utxo=witness_utxo,
        index=0,
        sighash_type=int(SIGHASH_ALL),
        witness_script=witness_script,
    )

    psbt_out = PSBT_Output(index=0)

    psbt = PartiallySignedTransaction(
        unsigned_tx=unsigned_tx,
        inputs=[psbt_in],
        outputs=[psbt_out],
    )

    print("\n[Debug] Initial unsigned PSBT:")
    print(f"  Unsigned txid      : {b2lx(unsigned_tx.GetTxid())}")
    print(f"  Input value (sats) : {utxo_value}")
    print(f"  Output value (sats): {send_value}")

    return psbt, witness_script, keys


def sign_psbt_input_with_key(
    psbt: PartiallySignedTransaction,
    witness_script: CScript,
    key: CCoinKey,
    utxo_value: int,
    label: str,
) -> None:
    tx = psbt.unsigned_tx

    sighash = SignatureHash(
        witness_script,
        tx,
        0,
        SIGHASH_ALL,
        amount=utxo_value,
        sigversion=SIGVERSION_WITNESS_V0,
    )

    sig = key.sign(sighash) + bytes([int(SIGHASH_ALL)])

    if psbt.inputs[0].partial_sigs is None:
        psbt.inputs[0].partial_sigs = {}

    psbt.inputs[0].partial_sigs[key.pub] = sig

    print(f"\n[Debug] {label} signed the PSBT:")
    print(f"  Signer pubkey        : {key.pub.hex()}")
    print(f"  Signature (hex)      : {sig.hex()}")
    print(f"  Total partial sigs   : {len(psbt.inputs[0].partial_sigs)}")


def finalize_psbt_multisig(
    psbt: PartiallySignedTransaction,
    witness_script: CScript,
) -> CMutableTransaction:
    psbt_in = psbt.inputs[0]

    if not psbt_in.partial_sigs or len(psbt_in.partial_sigs) < 2:
        raise ValueError("Need at least 2 signatures in partial_sigs to finalize 2-of-3.")

    # CHECKMULTISIG expects signatures to be ordered according to the
    # pubkey order that appears in the multisig script (witness_script),
    # not lexicographically by pubkey bytes. So we scan the witness_script
    # for pubkey pushes and pick signatures in that order.
    pubkeys_in_script_order = []
    for op in witness_script:
        if isinstance(op, (bytes, bytearray)) and len(op) in (33, 65):
            pubkeys_in_script_order.append(op)

    ordered_sigs = []
    ordered_pubkeys = []
    for pk_bytes in pubkeys_in_script_order:
        for pk_obj, sig in psbt_in.partial_sigs.items():
            if bytes(pk_obj) == pk_bytes:
                ordered_pubkeys.append(pk_obj)
                ordered_sigs.append(sig)
                break
        if len(ordered_sigs) >= 2:
            break

    if len(ordered_sigs) < 2:
        raise ValueError("Could not match 2 signatures to pubkeys in witness_script order.")

    # Build final witness: OP_0 (dummy) <sig1> <sig2> <witness_script>
    witness = CScriptWitness([b"", ordered_sigs[0], ordered_sigs[1], bytes(witness_script)])

    psbt_in.final_script_sig = CScript([])
    psbt_in.final_script_witness = witness

    print("\n[Debug] Finalizing PSBT:")
    print("  Using pubkeys in script order:")
    print(f"    1: {ordered_pubkeys[0].hex()}")
    print(f"    2: {ordered_pubkeys[1].hex()}")
    print("  Witness stack: [OP_0, sig1, sig2, witness_script]")
    # Clear non-final fields as required by python-bitcointx PSBT rules
    # Once final_script_witness is set, partial_sigs and witness_script
    # must not remain on the finalized PSBT_Input.
    psbt_in.partial_sigs = None
    psbt_in.witness_script = None

    final_tx = psbt.extract_transaction()

    return final_tx


def main() -> None:
    try:
        (
            wif_a,
            wif_b,
            wif_c,
            prev_txid_hex,
            vout,
            witness_script_hex,
            utxo_value,
            dest_address,
            fee,
        ) = read_inputs()

        psbt, witness_script, keys = build_unsigned_psbt_1in1out_p2wsh(
            wif_a,
            wif_b,
            wif_c,
            prev_txid_hex,
            vout,
            witness_script_hex,
            utxo_value,
            dest_address,
            fee,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")
        return

    print("\n=== Step 1: Unsigned PSBT created ===")

    # Simulate sequential signing: A -> B -> (C optional)
    try:
        sign_psbt_input_with_key(psbt, witness_script, keys[0], utxo_value, "Signer A")
        print("\n=== Step 2: PSBT after A's signature ===")
    except Exception as exc:  # noqa: BLE001
        print(f"Error during A's signing: {exc.__class__.__name__}: {exc}")
        return

    try:
        sign_psbt_input_with_key(psbt, witness_script, keys[1], utxo_value, "Signer B")
        print("\n=== Step 3: PSBT after B's signature ===")
    except Exception as exc:  # noqa: BLE001
        print(f"Error during B's signing: {exc.__class__.__name__}: {exc}")
        return

    # Optionally, C could also sign; for 2-of-3 we already have 2 signatures

    try:
        final_tx = finalize_psbt_multisig(psbt, witness_script)
    except Exception as exc:  # noqa: BLE001
        print(f"Error during finalization: {exc.__class__.__name__}: {exc}")
        return

    raw_hex = b2x(final_tx.serialize())
    txid = b2lx(final_tx.GetTxid())

    print("\n=== Final signed transaction (2-of-3 P2WSH, 1-in-1-out) ===")
    print(f"TxID      : {txid}")
    print(f"Raw (hex) : {raw_hex}")

    print("\nYou can broadcast this transaction by:")
    print("  - Using your own signet node: bitcoin-cli -signet sendrawtransaction '<rawhex>'")
    print("  - Or via a block explorer that supports signet (paste the raw hex)")


if __name__ == "__main__":
    main()
