import argparse
import json
import os
from pathlib import Path

import vana
from dotenv import load_dotenv

load_dotenv()

# ───────────────────────── helper ──────────────────────────

def _read_keystore(path: str):
    """Return (private_key, address) from a simple JSON keystore."""
    ks_path = Path(os.path.expanduser(path)).resolve()
    if not ks_path.is_file():
        raise FileNotFoundError(f"Keystore file {ks_path} not found")
    data = json.loads(ks_path.read_text())
    try:
        return data["privateKey"], data.get("address", "unknown")
    except KeyError as exc:
        raise ValueError(f"'privateKey' missing in {ks_path}") from exc

# ───────────────────────── existing hooks ──────────────────

def check_config(cls, config: vana.Config):
    """Checks/validates the config namespace object."""
    vana.logging.check_config(config)


def add_args(cls, parser):
    """Adds relevant arguments to the parser for operation."""
    parser.add_argument(
        "--node.environment",
        type=str,
        help="The environment the node is running in (development, production).",
        default=os.getenv("ENVIRONMENT", "production"),
    )

    # Allow a keystore JSON instead of mnemonic
    parser.add_argument(
        "--wallet.keystore",
        type=str,
        help="Path to JSON keystore with privateKey (or set HOTKEY_KEYSTORE env)",
        default=os.getenv("HOTKEY_KEYSTORE"),
    )


def default_config(cls):
    """Returns the configuration object specific to this node."""
    parser = argparse.ArgumentParser()
    vana.Wallet.add_args(parser)
    vana.ChainManager.add_args(parser)
    vana.Client.add_args(parser)
    vana.NodeServer.add_args(parser)
    vana.logging.add_args(parser)
    cls.add_args(parser)

    cfg = vana.Config(parser)

    # ── Wallet selection precedence ──
    # 1. explicit keystore path (CLI or env)
    keystore_path = getattr(cfg.wallet, "keystore", None)
    if keystore_path:
        priv, addr = _read_keystore(keystore_path)
        cfg.wallet.private_key = priv
        cfg.wallet.mnemonic = None  # ensure mnemonic not used
        vana.logging.info(
            f"Using wallet keystore {keystore_path} (address={addr})"
        )
    # 2. mnemonic already set via args/env → nothing to change; log for clarity
    elif getattr(cfg.wallet, "mnemonic", None):
        vana.logging.info("Using wallet mnemonic provided via HOTKEY_MNEMONIC/CLI")
    # 3. fallback to default wallet resolution in vana.Wallet
    else:
        vana.logging.info("No keystore or mnemonic provided, falling back to default wallet file in ~/.vana/wallets")

    # Set custom wallet path, coldkey name, and hotkey name from env, with defaults
    wallet_path = os.getenv('VANA_WALLET_PATH', os.path.expanduser('~/.vana/wallets/refiner'))
    coldkey_name = os.getenv('VANA_COLDKEY_NAME', 'refiner')
    hotkey_name = os.getenv('VANA_HOTKEY_NAME', 'refiner')

    if hasattr(cfg.wallet, 'path'):
        cfg.wallet.path = wallet_path
    else:
        setattr(cfg.wallet, 'path', wallet_path)

    if hasattr(cfg.wallet, 'coldkey'):
        cfg.wallet.coldkey = coldkey_name
    else:
        setattr(cfg.wallet, 'coldkey', coldkey_name)

    if hasattr(cfg.wallet, 'hotkey'):
        cfg.wallet.hotkey = hotkey_name
    else:
        setattr(cfg.wallet, 'hotkey', hotkey_name)

    return cfg