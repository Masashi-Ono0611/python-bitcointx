# PSBT SIGHASH Demo Notes

This file summarizes the small demo scripts used to explore PSBT and SIGHASH behavior with `python-bitcointx` on Signet. The focus is on P2WPKH inputs and different SIGHASH modes.

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

## 2. p2wpkh_psbt_sighash_all_1in1out.py

**Purpose**
- Minimal PSBT demo for a **1-input / 1-output** P2WPKH transaction using `SIGHASH_ALL`.
- Show a fully standard, simple payment that can be broadcast on Signet.

**Structure**
- Single P2WPKH input, spending one UTXO.
- Single P2WPKH output to a destination address.
- Uses PSBT to:
  - define the unsigned transaction,
  - attach UTXO information (`CTxOut` in the PSBT input), and
  - sign with `SIGHASH_ALL`.

**What it demonstrates**
- `SIGHASH_ALL` commits to:
  - all inputs, and
  - all outputs.
- After signing, **any modification** to:
  - amounts of outputs,
  - destination addresses,
  - number/order of outputs,
  - or inputs
  will invalidate the signature.

**Behavior**
- If you try to edit the raw hex of this transaction after signing (e.g. change the output address or amount) and broadcast it, the node rejects the transaction with a script verification error (signature becomes invalid).

---

## 3. p2wpkh_psbt_sighash_all_1in2out.py

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

---

## 4. p2wpkh_psbt_sighash_single_anyonecanpay_1in1out.py

**Purpose**
- Demonstrate `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY` in the **simplest 1-input / 1-output** scenario.
- Provide a baseline to compare with the more interesting 1-in-2-out case.

**Structure**
- One P2WPKH input.
- One P2WPKH output.
- PSBT is constructed with UTXO information and signed using `SIGHASH_SINGLE|SIGHASH_ANYONECANPAY`.

**What it demonstrates**
- With only one input and one output:
  - `SIGHASH_SINGLE` and `SIGHASH_ALL` **behave similarly** in practice, because there is a one-to-one mapping between input #0 and output #0.
  - `SIGHASH_ANYONECANPAY` still means that the signature does not commit to any other inputs (but since there is only one, the effect is not visible).
- This script mainly serves as a conceptual stepping stone, before adding a second output.

---

## 5. p2wpkh_psbt_sighash_single_anyonecanpay_1in2out.py

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
