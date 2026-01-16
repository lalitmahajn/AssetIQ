
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from typing import Any

router = APIRouter(prefix="/hq", tags=["hq-proxy"])

# HQ service DNS name in docker-compose network is "hq_backend"
# Port 8100 is where the API runs.
HQ_API_INTERNAL = "http://hq_backend:8100"

@router.get("/{path:path}")
async def proxy_hq_get(path: str, request: Request):
    """
    Proxies GET requests starting with /hq/... to the HQ backend.
    Example: GET /hq/compare/downtime -> GET http://hq_backend:8100/hq/compare/downtime
    """
    # Reconstruct URL: 
    # The router prefix is /hq, so 'path' will be everything after /hq/
    # Target: http://hq_backend:8100/hq/{path}
    
    target_url = f"{HQ_API_INTERNAL}/hq/{path}"
    
    # Forward query parameters
    params = dict(request.query_params)
    
    # Forward Authorization header
    headers = {}
    if "authorization" in request.headers:
        headers["Authorization"] = request.headers["authorization"]

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(target_url, params=params, headers=headers, timeout=5.0)
            
            # Forward status code if error
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=resp.text or "HQ Error")
            
            # Forward JSON content
            return resp.json()
            
        except httpx.RequestError as exc:
            print(f"HQ Proxy Error: {exc}")
            raise HTTPException(status_code=502, detail=f"HQ Connection Failed")
