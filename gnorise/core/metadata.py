import httpx
import asyncio
from typing import Dict, Optional, Any
from pydantic import BaseModel

class PackageMetadata(BaseModel):
    name: str
    description: Optional[str] = "No description available"
    latest_version: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None

class MetadataFetcher:
    NPM_REGISTRY_URL = "https://registry.npmjs.org/{pkg}/latest"

    async def fetch(self, package_name: str) -> PackageMetadata:
        """Fetch live metadata from npm registry."""
        url = self.NPM_REGISTRY_URL.format(pkg=package_name)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return PackageMetadata(
                        name=package_name,
                        description=data.get("description"),
                        latest_version=data.get("version"),
                        homepage=data.get("homepage"),
                        license=data.get("license")
                    )
        except Exception:
            pass # Fallback to empty metadata on error
            
        return PackageMetadata(name=package_name)

    async def fetch_batch(self, packages: list[str]) -> Dict[str, PackageMetadata]:
        """Fetch metadata for multiple packages concurrently."""
        tasks = [self.fetch(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks)
        return {res.name: res for res in results}
