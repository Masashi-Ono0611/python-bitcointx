#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from bitcointx import select_chain_params, set_custom_secp256k1_path
from bitcointx.signmessage import BitcoinMessage, SignMessage, VerifyMessage
from bitcointx.wallet import CCoinKey, P2PKHCoinAddress


set_custom_secp256k1_path(
    "/Users/masashi_mac_ssd/Developer/secp256k1/.libs/libsecp256k1.dylib",
)


def read_inputs() -> tuple[str, str, str]:
    print("=== python-bitcointx: basic sign-message demo ===\n")

    wif = input("Private key (WIF, required): ").strip()
    message = input("Message to sign (required): ").strip()

    if not wif or not message:
        raise ValueError("Private key (WIF) and message are required.")

    # Always use signet for this demo
    chain_name = "bitcoin/signet"

    return wif, message, chain_name


def sign_and_verify(wif: str, msg: str, chain_name: str) -> None:
    select_chain_params(chain_name)

    key = CCoinKey(wif)
    address = P2PKHCoinAddress.from_pubkey(key.pub)

    btc_message = BitcoinMessage(msg)
    signature = SignMessage(key, btc_message)

    verified = VerifyMessage(address, btc_message, signature)

    print("\n=== Result ===")
    print(f"Network   : {chain_name}")
    print(f"Address   : {address}")
    print(f"Message   : {msg}")
    print(f"Signature : {signature.decode('ascii')}")
    print(f"Verified  : {verified}")

    if not verified:
        print("\nWARNING: Signature verification returned False.")


def main() -> None:
    try:
        wif, msg, chain_name = read_inputs()
        sign_and_verify(wif, msg, chain_name)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc.__class__.__name__}: {exc}")


if __name__ == "__main__":
    main()
