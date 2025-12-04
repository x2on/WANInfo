from fastapi import FastAPI, HTTPException
import httpx
import os
import ssl
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="WANInfo",
    description="WANInfo Proxy API - consuming Unifi REST API and get WAN1 / WAN2 Status",
    version="1.0.0",
)

EXTERNAL_API_BASE_URL = os.getenv("EXTERNAL_API_BASE_URL")
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY")
CA_CERT_PATH = os.getenv("CA_CERT_PATH", "certs/ca.pem") 

@app.get("/status")
async def get_status():
    if not EXTERNAL_API_BASE_URL or not EXTERNAL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="EXTERNAL_API_BASE_URL or EXTERNAL_API_KEY missing."
        )

    url = f"{EXTERNAL_API_BASE_URL}"
    headers = {
        "X-API-KEY": EXTERNAL_API_KEY,
        "Accept": "application/json",
    }

    if os.path.isfile(CA_CERT_PATH):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations(cafile=CA_CERT_PATH)
        verify_mode = ssl_ctx
    else:
        verify_mode = False

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=verify_mode) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error consuming external REST API: {exc}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Error external REST API: {response.status_code} {response.text}"
        )

    external_data = response.json()

    transformed = {
        "online": external_data["data"][1]["wan1"]["up"] or external_data["data"][1]["wan2"]["up"],
        "failover": not external_data["data"][1]["wan1"]["up"],
        "wan1": {
            "up": external_data["data"][1]["wan1"]["up"],
            "ip": external_data["data"][1]["wan1"]["ip"]
        },
        "wan2": {
            "up": external_data["data"][1]["wan2"]["up"],
            "ip": external_data["data"][1]["wan2"]["ip"]
        },
        "ip": external_data["data"][1]["ip"],
        "last_wan_ip": external_data["data"][1]["last_wan_ip"]
    }

    return transformed
