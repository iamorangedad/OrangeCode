import os
import re


def extract_filename_from_code(code, language):
    """Extract meaningful filename from code content based on business logic"""
    code_lower = code.lower()

    # Python naming patterns
    if language in ["python", "py"]:
        # Class detection
        class_match = re.search(r"class\s+(\w+)", code)
        if class_match:
            return f"{class_match.group(1).lower()}.py"

        # Flask/FastAPI app
        if "flask" in code_lower or "app = flask" in code_lower:
            return "flask_app.py"
        if "fastapi" in code_lower or "app = fastapi" in code_lower:
            return "fastapi_app.py"

        # Function detection
        func_match = re.search(r"def\s+(\w+)\s*\(", code)
        if func_match:
            return f"{func_match.group(1)}.py"

        # Django models
        if "models" in code_lower and "django" in code_lower:
            return "models.py"

        # Data processing
        if "pandas" in code_lower or "dataframe" in code_lower:
            return "data_processor.py"

        # API client
        if "request" in code_lower and "api" in code_lower.split():
            return "api_client.py"

        # Database
        if "sql" in code_lower or "database" in code_lower:
            return "database.py"

        # Utils/Helper
        if "def " in code and code.count("def ") > 2:
            return "utils.py"

    # JavaScript naming patterns
    elif language in ["javascript", "js", "typescript", "ts"]:
        # React component
        if "react" in code_lower or "function\s+\w+\(\)" in code:
            comp_match = re.search(r"function\s+(\w+)\s*\(", code)
            if comp_match:
                return f"{comp_match.group(1)}.js"
            const_match = re.search(r"const\s+(\w+)\s*=\s*\(\)", code)
            if const_match:
                return f"{const_match.group(1)}.jsx"
            return "component.jsx"

        # Express server
        if "express" in code_lower:
            return "server.js"

        # API endpoint
        if "app.get" in code or "app.post" in code or "router" in code_lower:
            return "api_routes.js"

        # Utility functions
        if code.count("function") > 1 or code.count("const") > 3:
            return "utils.js"

        # Config file
        if "config" in code_lower or "export" in code and "const" in code:
            return "config.js"

    # Bash naming patterns
    elif language in ["bash", "shell", "sh"]:
        # Deployment script
        if "docker" in code_lower or "deploy" in code_lower:
            return "deploy.sh"

        # Backup script
        if "backup" in code_lower or "tar" in code_lower:
            return "backup.sh"

        # Install script
        if "apt" in code_lower or "yum" in code_lower or "pip" in code_lower:
            return "install.sh"

        # Setup script
        if "setup" in code_lower or "export" in code_lower:
            return "setup.sh"

    return None


def get_unique_filename(base_name):
    """Generate unique filename to avoid overwriting existing files"""
    if not os.path.exists(base_name):
        return base_name

    name, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(f"{name}_{counter}{ext}"):
        counter += 1
    return f"{name}_{counter}{ext}"
