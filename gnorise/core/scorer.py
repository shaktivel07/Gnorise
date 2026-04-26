from enum import Enum
from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Dict, Optional

class UsageStatus(str, Enum):
    USED = "used"
    POSSIBLY_USED = "possibly_used"
    UNUSED = "unused"

@dataclass
class Evidence:
    type: Literal["static", "dynamic", "framework", "config", "transitive", "test", "uncertain"]
    weight: int
    files: List[str]
    explanation: str

@dataclass  
class DepScore:
    name: str
    version: str
    is_dev: bool = False
    is_framework_managed: bool = False
    
    def calculate(self, usage_data: Dict[str, List[str]]) -> Tuple[UsageStatus, int, List[Evidence]]:
        """
        Calculates status, confidence score, and returns evidence.
        """
        score = 0
        evidence: List[Evidence] = []
        
        static_files = usage_data.get("static", [])
        if static_files:
            # 40 per file, cap at 80
            pts = min(80, 40 * len(static_files))
            score += pts
            evidence.append(Evidence("static", pts, static_files, f"Found in {len(static_files)} files via static import"))
        
        if len(static_files) >= 2:
            pts = 10
            score += pts
            evidence.append(Evidence("static", 10, static_files, "Multi-file usage bonus"))
        
        if self.is_framework_managed:
            pts = 30
            score += pts
            evidence.append(Evidence("framework", 30, [], "Managed by framework or common tool convention"))
        
        dynamic_files = usage_data.get("dynamic", [])
        if dynamic_files:
            pts = 20
            score += pts
            evidence.append(Evidence("dynamic", 20, dynamic_files, "Loaded dynamically"))
            
        uncertain_files = usage_data.get("uncertain", [])
        if uncertain_files:
            pts = -15
            score += pts
            evidence.append(Evidence("uncertain", pts, uncertain_files, "Uncertain dynamic imports detected"))
        
        if self.is_dev and not static_files and not dynamic_files:
            pts = -10
            score += pts
            evidence.append(Evidence("test", -10, [], "Dev dependency without direct code usage"))
        
        if not static_files and not dynamic_files and not self.is_framework_managed:
            pts = -40
            score += pts
            evidence.append(Evidence("transitive", -40, [], "No direct usage found"))
        
        # Floor for DevDeps/Framework tools
        if (self.is_dev or self.is_framework_managed) and score < 20:
            score = max(score, 20)

        score = max(0, min(100, score))
        if score >= 70: 
            status = UsageStatus.USED
        elif score >= 30: 
            status = UsageStatus.POSSIBLY_USED
        else: 
            status = UsageStatus.UNUSED
        
        return status, score, evidence
