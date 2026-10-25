"""Start the local preview with its fixed demo account and additive sample dataset.

Explicit development entry point; never called by Docker or the normal API startup.
Configuration/secrets live in ignored .env.preview, not the source tree or logs.
"""

import argparse
import getpass
import os
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]


def configure_preview(password=None):
    config = ROOT / ".env.preview"
    config.touch(mode=0o600, exist_ok=True)
    config.chmod(0o600)
    values = dotenv_values(config)
    password = password or values.get("STUDYFLOW_DEMO_PASSWORD")
    if not password:
        password = getpass.getpass("Preview demo password: ")
    if not password:
        raise ValueError("The preview demo password is required.")
    if password != values.get("STUDYFLOW_DEMO_PASSWORD"):
        set_key(config, "STUDYFLOW_DEMO_PASSWORD", password)
    key = values.get("JWT_SECRET_KEY") or secrets.token_hex(32)
    if not values.get("JWT_SECRET_KEY"):
        set_key(config, "JWT_SECRET_KEY", key)
    # Deliberately override DB settings here only; never seed an environment's MySQL DB.
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{ROOT / 'preview.db'}"
    os.environ["JWT_SECRET_KEY"] = key
    os.environ["UPLOAD_DIR"] = str(ROOT / "apps" / "api" / "uploads")
    return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    password = configure_preview(os.environ.get("STUDYFLOW_DEMO_PASSWORD"))
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    import httpx
    import uvicorn
    from app.main import app
    from seed_preview import seed_preview

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def preview_lifespan(application):
        async with original_lifespan(application):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application),
                base_url="http://preview",
                timeout=60,
            ) as client:
                try:
                    result = await seed_preview(client, password)
                    print("Preview demo workspace ready:", result, flush=True)
                except RuntimeError as error:
                    # Edited demo content or a credential mismatch must not lock out the app.
                    print(
                        f"Preview demo setup incomplete: {error}. Existing records kept; API remains available.",
                        flush=True,
                    )
            yield

    app.router.lifespan_context = preview_lifespan
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
