# PSBT SIGHASH Demo Notes

**Quick map of main teaching scripts**
- `p2wpkh_sighash_all_1in2out.py` … Baseline SIGHASH_ALL behavior for 1-in-2-out P2WPKH.
- `p2wpkh_sighash_single_anyonecanpay_1in2out.py` … SIGHASH_SINGLE|ANYONECANPAY behavior for 1-in-2-out P2WPKH, showing mutable vs committed outputs.
- `mutate_output1_address_1in2out.py` … Post-signing mutation of output #1 (address) to demonstrate what SIGHASH_SINGLE|ANYONECANPAY allows.
- `p2wpkh_simple_signet_transaction.py` … Raw P2WPKH single-sig example (no PSBT), for direct BIP143-style signing.
- `p2wsh_2of3_create_address.py` … 2-of-3 P2WSH Treasury address + witnessScript generator (multi-sig setup).
- `p2wsh_2of3_spend_multisig.py` … Practical 2-of-3 P2WSH multisig spend using PSBT (A/B/C sequential signing, final broadcastable tx).

This file summarizes the small demo scripts used to explore PSBT and SIGHASH behavior with `python-bitcointx` on Signet. The focus is on P2WPKH inputs, SIGHASH modes, and a practical 2-of-3 P2WSH multisig workflow.

---

## 1. mutate_output1_address_1in2out.py

**Purpose**
- Demonstrate how a transaction signed with `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` can be modified **after signing**.
- Specifically, show that changing the **destination address of output #1** (while keeping its amount constant) does **not** break the signature, when the signature only commits to output #0.

**What the script does**
- Takes a **1-input / 2-output** raw transaction hex that was already signed and broadcastable.
- Parses the transaction and replaces the **scriptPubKey (address)** of **output index 1** with a new address, keeping:
  - the index (still vout=1), and
  - the amount (value in satoshis)
  unchanged.
- Serializes the mutated transaction and prints the new raw hex so it can be broadcast to Signet.

**Key observations from experiments**
- For a transaction where the input is signed with `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` and commits to **output #0**:
  - Modifying **output #1's address only** (same amount) still results in a **valid transaction**.
  - The network accepts the mutated transaction; `CHECKSIG` passes.
- Conceptually:
  - `SIGHASH_SINGLE` (with one input and at least two outputs) commits only to the output whose index equals the input index.
  - `SIGHASH_ANYONECANPAY` restricts the commitment to **only this input**, ignoring other inputs.
  - As a result, all **non-committed outputs** (here, output #1) are free to be changed by a third party.

---

## 2. p2wpkh_sighash_all_1in2out.py

**Purpose**
- Extend the `SIGHASH_ALL` demo to a **1-input / 2-output** P2WPKH transaction.
- Contrast `SIGHASH_ALL` with `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` in the 1-in-2-out setting.

**Structure**
- One P2WPKH input.
- Two P2WPKH outputs, for example:
  - Output #0: main payment.
  - Output #1: change or an additional payment.
- The PSBT is built and signed with `SIGHASH_ALL`.

**What it demonstrates**
- Under `SIGHASH_ALL`, the signature commits to **both outputs**:
  - Output #0 amount and scriptPubKey.
  - Output #1 amount and scriptPubKey.
- Therefore, **any mutation of either output** (amount or address), after signing, will cause the signature to fail.

**Experimental result**
- When this `SIGHASH_ALL` transaction is modified after signing (for example by changing output #1's address), Signet rejects it with an error like:
  - `mandatory-script-verify-flag-failed (Script evaluated without error but finished with a false/empty top stack element)`
- This confirms that `SIGHASH_ALL` protects **all outputs**, not just the one that "belongs" to the signer.

## 3. p2wpkh_sighash_single_anyonecanpay_1in2out.py

**Purpose**
- Core educational demo for `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` with **1 input and 2 outputs**.
- Show clearly which parts of the transaction are committed by the signature, and which parts remain mutable.

**Structure**
- One P2WPKH input, usually at index 0.
- Two outputs:
  - Output #0: the output that the signer cares about and wants to lock in.
  - Output #1: an additional output that is *not* covered by the signature.
- The PSBT is created and signed with `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` for input index 0.

**Commitment behavior**
- `SIGHASH_SINGLE` (for input index 0):
  - Commits to **output[0] only** (amount and scriptPubKey).
  - Does **not** commit to outputs with other indices (e.g. output[1]).
- `SIGHASH_ANYONECANPAY`:
  - Commits only to this input (index 0).
  - Does **not** commit to any other inputs (if they are later added).

**What it demonstrates**
- For this transaction:
  - Changing **output #0** (amount or address) after signing will invalidate the signature and the network will reject the transaction.
  - Changing **output #1** (amount or address), while keeping the overall transaction valid (sum of outputs ≤ sum of inputs), will **not** affect the signature.
- Combined with `mutate_output1_address_1in2out.py`, you can:
  - Sign a transaction once.
  - Modify output #1 to send funds to a different address.
  - Broadcast the mutated transaction and see that it is still accepted by Signet.

---

## 6. Comparison summary: SIGHASH_ALL vs SIGHASH_SINGLE|ANYONECANPAY

**SIGHASH_ALL (1-in-2-out)**
- Commits to:
  - all inputs, and
  - all outputs.
- After signing:
  - You **cannot** change any output address or amount.
  - You **cannot** add/remove/reorder outputs.
- If you try, script verification fails with `mandatory-script-verify-flag-failed`.

**SIGHASH_SINGLE|SIGHASH_ANYONECANPAY (1-in-2-out, input index 0)**
- Commits to:
  - input #0, and
  - output #0 only.
- Does **not** commit to:
  - any other inputs,
  - any other outputs (e.g. output #1).
- After signing:
  - You **cannot** change output #0.
  - You **can** change output #1 (address and/or amount, as long as the transaction remains valid in terms of value).

**Practical intuition**
- `SIGHASH_ALL` is the "normal" secure payment: the signer locks in the entire transaction.
- `SIGHASH_SINGLE|ANYONECANPAY` is more flexible: it allows someone to guarantee one specific output for themselves, while leaving room for others to modify remaining outputs or add inputs.

---

## 7. Relationship between raw transaction editing and signatures

- You can always **edit raw transaction hex locally** with any tool or script; there is no cryptographic restriction on modifying bytes.
- What matters is whether, after editing, the transaction still passes **consensus rules**:
  - script evaluation (`CHECKSIG` etc.),
  - value conservation (sum of inputs ≥ sum of outputs),
  - standardness and policy rules.
- The SIGHASH mode defines **which parts of the transaction are covered by the signature hash**. Only those parts are protected against tampering.
- These demos show concretely:
  - With `SIGHASH_ALL`, almost any post-signing mutation breaks the signature.
  - With `SIGHASH_SINGLE|ANYONECANPAY`, certain fields (like non-committed outputs) can be changed without invalidating the original signature.

---

## 6. PSBT vs SIGHASH: orthogonal concepts

- **PSBT (Partially Signed Bitcoin Transaction)** is a **format / container** defined by BIP174 (and extended by BIP370), used to carry:
  - the unsigned transaction (`unsigned_tx`),
  - extra data needed for signing (UTXO info, scripts, BIP32 paths, etc.), and
  - partial or final signatures.
- **SIGHASH (e.g. `SIGHASH_ALL`, `SIGHASH_SINGLE|ANYONECANPAY`)** controls **what parts of the transaction a given signature commits to**.
- These are **independent axes**:
  - You can use `SIGHASH_ALL` or `SIGHASH_SINGLE|ANYONECANPAY` **inside** a PSBT.
  - You can also sign without PSBT, directly over raw transactions.
- Whether something is a "PSBT" depends on **using the PSBT format (BIP174/370)**, not on which SIGHASH type is used.

---

## 7. Single-sig P2WPKH: raw tx example

This section briefly recalls the direct raw P2WPKH example used for comparison.

### 7.1 Raw P2WPKH transaction (`p2wpkh_simple_signet_transaction.py`)

**Characteristics**
- Builds an unsigned `CMutableTransaction` directly.
- Computes the BIP143-style sighash with:
  - `script_code` (P2PKH-like script),
  - the unsigned tx,
  - input index,
  - `SIGHASH_ALL`,
  - `amount=utxo_value`,
  - `sigversion=SIGVERSION_WITNESS_V0`.
- Immediately creates the final witness:
  - `CScriptWitness([sig, pubkey])` for P2WPKH.
- Verifies the script with `VerifyScript` and then serializes the final raw transaction.

**What it shows**
- A classic, direct way to build and sign a SegWit P2WPKH transaction.
- All information (UTXO amount, script, etc.) is handled inside the script logic; there is no portable "draft" format.

---

## 7. P2WSH 2-of-3 multisig address and PSBT spend

This section summarizes the 2-of-3 P2WSH multisig Treasury example on Signet.

### 8.1 `p2wsh_2of3_create_address.py`

**Purpose**
- Create a Signet 2-of-3 P2WSH multisig Treasury address from three WIF private keys.

**What the script does**
- Reads three Signet WIFs for signers A, B, and C.
- Converts them to `CCoinKey` and extracts their compressed pubkeys.
- Builds a 2-of-3 multisig `witnessScript`:
  - `OP_2 <pubA> <pubB> <pubC> OP_3 OP_CHECKMULTISIG`.
- Prints debug information:
  - Each pubkey in hex.
  - The multisig `witnessScript` in hex.
- Derives the P2WSH Signet address from the `witnessScript`:
  - `P2WSHBitcoinSignetAddress.from_redeemScript(witnessScript)`.
- Prints:
  - P2WSH Treasury address (e.g. `tb1q...`),
  - `witnessScript` hex,
  - resulting P2WSH scriptPubKey.

**How to use it**
- Run the script once to obtain a Treasury P2WSH address.
- Fund this P2WSH address on Signet (e.g. 10,000 sats) to create a UTXO.
- Keep the `witnessScript` hex and the three WIFs for future spending.

### 10.2 `p2wsh_2of3_spend_multisig.py`

**Purpose**
- Demonstrate a full 2-of-3 P2WSH multisig spend using PSBT on Signet.
- Show a realistic workflow where multiple signers (A, B, C) sign a PSBT in sequence, and the final transaction is broadcast.

**Inputs (CLI)**
- WIF for signer A (WIF, Signet).
- WIF for signer B (WIF, Signet).
- WIF for signer C (WIF, Signet).
- UTXO information:
  - `prev_txid` (hex, big-endian),
  - `vout` (output index),
  - `value` (sats).
- `witnessScript` hex (from the address creation script).
- Destination address (any Signet P2PKH / P2WPKH / P2WSH).
- Fee in sats.

**PSBT construction**
- Rebuilds the same `witnessScript` from hex.
- Derives the P2WSH address and scriptPubKey, assuming the UTXO is exactly that P2WSH.
- Constructs a 1-in / 1-out unsigned tx:
  - Input: the 2-of-3 P2WSH UTXO.
  - Output: destination address with `utxo_value - fee` sats.
- Creates `witness_utxo = CTxOut(utxo_value, p2wsh_scriptPubKey)`.
- Builds a `PSBT_Input` containing:
  - `unsigned_tx`,
  - `utxo = witness_utxo`,
  - `index = 0`,
  - `sighash_type = SIGHASH_ALL`,
  - `witness_script = witnessScript`.
- Wraps everything into a `PartiallySignedTransaction`.

**Sequential signing (A → B → C)**
- The script simulates A and B signing locally in sequence:
  - A computes the BIP143-style `SignatureHash` over the P2WSH input,
  - Appends `SIGHASH_ALL` and stores the signature in `psbt.inputs[0].partial_sigs[pubA]`.
  - B does the same, adding `psbt.inputs[0].partial_sigs[pubB]`.
- After A and B have signed, there are 2 signatures in `partial_sigs`, which is enough for 2-of-3.

**Finalization**
- `finalize_psbt_multisig`:
  - Scans the `witnessScript` to recover the pubkeys in script order (`pubA`, `pubB`, `pubC`).
  - Matches pubkeys with entries in `partial_sigs` and selects 2 signatures in that script order.
  - Builds the final witness stack:
    - `[OP_0, sig_for_pubX, sig_for_pubY, witnessScript]`.
  - Sets `final_script_sig = CScript([])` and `final_script_witness` to this stack.
  - Clears non-final PSBT fields (`partial_sigs`, `witness_script`) as required by python-bitcointx.
  - Calls `psbt.extract_transaction()` to produce the final raw transaction.

**What it demonstrates**
- A concrete PSBT-based 2-of-3 P2WSH multisig workflow on Signet:
  - Treasury address creation.
  - Funding the P2WSH UTXO.
  - Building a PSBT that contains unsigned tx, UTXO info, and the multisig script.
  - Multiple signers adding signatures via `partial_sigs`.
  - Finalizing into a broadcastable raw tx once enough signatures are present.
- How PSBT acts as a **container** for:
  - transaction structure,
  - UTXO metadata,
  - multisig scripts,
  - and partial signatures,
  independent of the chosen SIGHASH mode (`SIGHASH_ALL` in this demo).


---

## 8. Simple Taproot (P2TR) key-path spend

### 8.1 `p2tr_simple_signet_transaction.py`

**Purpose**
- Provide a minimal example of spending a Taproot (P2TR) UTXO on Signet using **key-path** (no script path) and Schnorr signatures.
- Serve as a direct counterpart to `p2wpkh_simple_signet_transaction.py`, but using P2TR instead of P2WPKH.

**What the script does**
- Reads from CLI:
  - WIF (Signet, compressed; used as the Taproot internal key),
  - UTXO info: `prev_txid` (big-endian hex), `vout`, `value` (sats),
  - `fee` (sats),
  - destination address (can be P2PKH / P2WPKH / P2TR).
- Derives a P2TR Signet address from the internal pubkey:
  - `P2TRBitcoinSignetAddress.from_pubkey(key.pub)` → `tb1p...` address.
- Assumes that the provided UTXO is an output to this P2TR address (its scriptPubKey must be `OP_1 <32-byte x-only key>`).
- Builds a 1-in / 1-out transaction:
  - Input: the P2TR UTXO.
  - Output: the specified destination address with `value - fee` sats.
- Computes the Taproot key-path signature hash:
  - Uses `SignatureHashSchnorr(tx, 0, spent_outputs)` where `spent_outputs` contains the P2TR scriptPubKey and amount.
- Produces a Schnorr signature with Taproot tweak:
  - `sig = key.sign_schnorr_tweaked(sighash)`.
- Sets the Taproot witness for key-path spend:
  - witness stack: `[sig]` (just the Schnorr signature).
- Leaves `scriptSig` empty (as required for P2TR).
- Calls `VerifyScript` with an empty flag set against the P2TR scriptPubKey for local validation.
- Prints the final TxID and raw hex for broadcasting to Signet.

**Contrast with `p2wpkh_simple_signet_transaction.py`**
- P2WPKH simple tx:
  - Address: `tb1q...` (v0 P2WPKH).
  - scriptPubKey: `OP_0 <20-byte-hash160(pubkey)>`.
  - Signature hashing: BIP143-style `SignatureHash(..., SIGVERSION_WITNESS_V0)`.
  - Witness: `[sig (ECDSA with hashtype), pubkey]`.
- P2TR simple tx:
  - Address: `tb1p...` (v1 P2TR).
  - scriptPubKey: `OP_1 <32-byte x-only output key>`.
  - Signature hashing: BIP341 `SignatureHashSchnorr(tx, idx, spent_outputs)`.
  - Witness (key-path): `[schnorr_sig]` (no pubkey in witness; the output key is in the scriptPubKey).

**What this teaches conceptually**
- How Taproot (P2TR) changes:
  - the scriptPubKey form (v0 keyhash vs v1 output key),
  - the signature hash algorithm (BIP143 vs BIP341),
  - the witness layout (pubkey included vs pubkey implied in scriptPubKey).
- That, from a high-level perspective, a P2TR key-path spend can feel as simple as a P2WPKH spend, but uses Schnorr and a different commitment structure under the hood.

### 8.2 Removed P2TR 2-of-3 CHECKSIGADD script-path demos

- **Exploratory scripts (now removed)**
  - `p2tr_2of3_create_address.py`
  - `p2tr_2of3_spend_multisig.py`
- **What they tried to do**
  - Implement a 2-of-3 Taproot script-path multisig using a CHECKSIGADD-style tapscript:
    - `<xonlyA> OP_CHECKSIG <xonlyB> OP_CHECKSIGADD <xonlyC> OP_CHECKSIGADD 2 OP_NUMEQUAL`.
  - Build a P2TR script tree + control block and spend the UTXO on Signet with two Schnorr signatures in the witness.
- **Why they were removed**
  - Locally, `VerifyScript` (with empty flags) accepted the tapscript spend, but Signet rejected the real transaction with:
    - `mandatory-script-verify-flag-failed (Invalid Schnorr signature)`.
  - The failure is likely due to subtle differences between python-bitcointx's experimental Tapscript `SignatureHashSchnorr` / schnorr-signing implementation and Bitcoin Core's BIP340/341/342 consensus rules for script-path spends.
  - Fixing this would require patching or extending python-bitcointx itself (library-internals level work), which is beyond the scope of these educational demos.
- **Takeaway**
  - The **completed, Signet-proven demos** in this repo are:
    - P2WSH 2-of-3 multisig (script-path via CHECKMULTISIG).
    - P2TR key-path single-sig.
  - The removed P2TR 2-of-3 CHECKSIGADD scripts are kept here only as design notes, not as working code.

---
