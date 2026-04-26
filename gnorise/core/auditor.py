import httpx
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel

class Vulnerability(BaseModel):
    id: str
    summary: Optional[str] = None
    details: Optional[str] = None
    severity: List[Dict[str, Any]] = []

class AuditResult(BaseModel):
    package: str
    vulnerabilities: List[Vulnerability] = []
    is_used: bool = False

class Auditor:
    OSV_API_URL = "https://api.osv.dev/v1/query"

    async def audit_package(self, name: str, version: str, is_used: bool) -> AuditResult:
        """Query OSV for vulnerabilities in a specific package version."""
        payload = {
            "version": version.strip("^~"),
            "package": {"name": name, "ecosystem": "npm"}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.OSV_API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    vulns = [Vulnerability(**v) for v in data.get("vulns", [])]
                    return AuditResult(package=name, vulnerabilities=vulns, is_used=is_used)
        except Exception:
            pass # Handle network errors silently for now
            
        return AuditResult(package=name, is_used=is_used)

    async def audit_all(self, dependencies: Dict[str, str], used_packages: Set[str]) -> List[AuditResult]:
        results = []
        for name, version in dependencies.items():
            res = await self.audit_package(name, version, name in used_packages)
            if res.vulnerabilities:
                results.append(res)
        return results
