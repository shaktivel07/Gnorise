from typing import Dict, Optional, List

# Awareness system for special packages
DEV_TOOLS = {
    "typescript": "TypeScript compiler",
    "eslint": "Linting tool",
    "prettier": "Code formatter",
    "vite": "Build tool",
    "webpack": "Bundler",
    "ts-node": "TypeScript runtime",
    "nodemon": "Process manager",
}

FRAMEWORK_TOOLS = {
    "next": "Next.js framework",
    "react": "React framework",
    "react-dom": "React DOM renderer",
    "express": "Express web framework",
}

TEST_TOOLS = {
    "jest": "Testing framework",
    "vitest": "Testing framework",
    "mocha": "Testing framework",
    "chai": "Assertion library",
    "cypress": "E2E testing framework",
}

BUILD_TOOLS = {
    "babel": "JS compiler",
    "@babel/core": "JS compiler core",
    "rollup": "Module bundler",
    "swc": "Fast compiler",
}

CONFIG_TO_PACKAGES = {
    "tsconfig.json": ["typescript", "ts-node"],
    "jsconfig.json": ["typescript"],
    ".eslintrc": ["eslint"],
    ".eslintrc.json": ["eslint"],
    ".eslintrc.js": ["eslint"],
    ".eslintrc.yml": ["eslint"],
    "prettier.config.js": ["prettier"],
    ".prettierrc": ["prettier"],
    "vite.config.ts": ["vite"],
    "vite.config.js": ["vite"],
    "webpack.config.js": ["webpack"],
    "jest.config.js": ["jest"],
    "vitest.config.ts": ["vitest"],
    "vitest.config.js": ["vitest"],
    "next.config.js": ["next"],
    "next.config.mjs": ["next"],
    "babel.config.js": ["babel", "@babel/core"],
    ".babelrc": ["babel", "@babel/core"],
}

def classify_special_package(name: str) -> Optional[str]:
    """Classify a package into a specific category based on its name."""
    name = name.lower()
    if name in DEV_TOOLS:
        return "dev_tool"
    if name in FRAMEWORK_TOOLS:
        return "framework"
    if name in TEST_TOOLS:
        return "test_tool"
    if name in BUILD_TOOLS:
        return "build_tool"
    return None

def get_package_description(name: str) -> str:
    """Get a human-readable description for a special package."""
    name = name.lower()
    return (
        DEV_TOOLS.get(name) or 
        FRAMEWORK_TOOLS.get(name) or 
        TEST_TOOLS.get(name) or 
        BUILD_TOOLS.get(name) or 
        "External dependency"
    )
