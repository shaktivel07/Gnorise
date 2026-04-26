from enum import Enum
from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Dict, Optional
from gnorise.core.awareness import classify_special_package

class UsageStatus(str, Enum):
    USED = "used"
    POSSIBLY_USED = "possibly_used"
    UNUSED = "unused"
    # Special categorized statuses
    DEV_TOOL = "dev_tool"
    FRAMEWORK = "framework"
    TEST_TOOL = "test_tool"
    BUILD_TOOL = "build_tool"

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
    used_by_config: bool = False
    
    def calculate(self, usage_data: Dict[str, List[str]]) -> Tuple[UsageStatus, int, List[Evidence]]:
        """
        Calculates status, confidence score, and returns evidence.
        """
        score = 0
        evidence: List[Evidence] = []
        
        # 1. Check for imports
        static_files = usage_data.get("static", [])
        if static_files:
            pts = min(80, 40 * len(static_files))
            score += pts
            evidence.append(Evidence("static", pts, static_files, f"Found in {len(static_files)} files via static import"))
        
        if len(static_files) >= 2:
            pts = 10
            score += pts
            evidence.append(Evidence("static", 10, static_files, "Multi-file usage bonus"))
        
        # 2. Check for config-based usage (e.g. tsconfig.json)
        if self.used_by_config:
            pts = 50
            score += pts
            evidence.append(Evidence("config", pts, [], "Active configuration file detected"))

        # 3. Dynamic & Uncertain usage
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

        # 4. Awareness System Overrides
        special_type = classify_special_package(self.name)
        
        if special_type:
            if special_type in ["dev_tool", "build_tool", "test_tool"]:
                score = max(score, 60)
                evidence.append(Evidence("framework", 60, [], f"Categorized as {special_type.replace('_', ' ')}"))
                status = UsageStatus[special_type.upper()]
            elif special_type == "framework":
                score = max(score, 85)
                evidence.append(Evidence("framework", 85, [], "Categorized as core framework"))
                status = UsageStatus.FRAMEWORK
        else:
            # Standard logic
            if self.is_dev and not static_files and not dynamic_files and not self.used_by_config:
                pts = -10
                score += pts
                evidence.append(Evidence("test", -10, [], "Dev dependency without direct code usage"))
            
            if not static_files and not dynamic_files and not self.used_by_config:
                pts = -40
                score += pts
                evidence.append(Evidence("transitive", -40, [], "No direct usage found"))

            score = max(0, min(100, score))
            if score >= 70: 
                status = UsageStatus.USED
            elif score >= 35: 
                status = UsageStatus.POSSIBLY_USED
            else: 
                status = UsageStatus.UNUSED
        
        # Final sanity check for confidence floors
        if self.is_dev and score < 30 and not special_type:
            score = 30
            
        return status, score, evidence
