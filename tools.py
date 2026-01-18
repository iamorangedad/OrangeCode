"""
Tool registration and management system
Decorator-based tool registration with dynamic permission management
"""

import inspect
from typing import Dict, List, Any, Callable, Optional, Type
from pydantic import BaseModel, Field
from enum import Enum


class PermissionLevel(Enum):
    """Permission level enumeration"""

    READ_ONLY = "read_only"  # Read-only permissions
    FILE_OPERATIONS = "file_ops"  # File operations permissions
    SHELL_COMMANDS = "shell_cmds"  # Shell commands permissions
    NETWORK_ACCESS = "network"  # Network access permissions
    SYSTEM_ADMIN = "system_admin"  # System administration permissions
    ALL_PERMISSIONS = "all"  # All permissions


class SkillRestriction(Enum):
    """Skill restriction enumeration"""

    FILE_MANAGER = "file_manager"  # File management skills
    CODE_ANALYZER = "code_analyzer"  # Code analysis skills
    SYSTEM_INFO = "system_info"  # System information skills
    DEVELOPER_ASSISTANT = "developer_assistant"  # Developer assistant skills
    SYSTEM_ADMIN = "system_admin"  # System administration skills
    ALL_SKILLS = "all"  # All skills


# Global tool registration table
REGISTERED_TOOLS: Dict[str, Dict[str, Any]] = {}

# Active skill permissions
ACTIVE_SKILL_PERMISSIONS: List[SkillRestriction] = []


def function_tool(
    name: str = None,
    description: str = None,
    permissions: List[PermissionLevel] = None,
    skill_types: List[SkillRestriction] = None,
):
    """
    Decorator for registering tools with metadata

    Args:
        name: Tool name
        description: Tool description
        permissions: Required permission list
        skill_types: Allowed skill type list
    """

    def decorator(func):
        # Get function signature and parameter model
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # Create Pydantic field
        fields = {}
        for param in params:
            field_type = (
                param.annotation if param.annotation != inspect.Parameter.empty else str
            )
            default_value = (
                param.default if param.default != inspect.Parameter.empty else ...
            )

            field_info = Field(
                default=default_value if default_value != ... else ...,
                description=f"Parameter: {param.name}",
            )
            fields[param.name] = (field_type, field_info)

        # Register tool
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"

        REGISTERED_TOOLS[tool_name] = {
            "function": func,
            "name": tool_name,
            "description": tool_description,
            "permissions": permissions or [PermissionLevel.READ_ONLY],
            "skill_types": skill_types or [SkillRestriction.ALL_SKILLS],
            "parameters": fields,
        }

        return func

    return decorator


class PermissionGuard:
    """Skill permission guard"""

    def __init__(self, active_skills: List[SkillRestriction] = None):
        """
        Initialize permission guard

        Args:
            active_skills: Active skill list
        """
        self.active_skills = active_skills or [SkillRestriction.ALL_SKILLS]
        self.skill_permissions: Dict[SkillRestriction, List[PermissionLevel]] = {}
        self._load_default_permissions()

    def _load_default_permissions(self):
        """Load default skill permission configuration"""
        self.skill_permissions = {
            SkillRestriction.FILE_MANAGER: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.FILE_OPERATIONS,
            ],
            SkillRestriction.CODE_ANALYZER: [PermissionLevel.READ_ONLY],
            SkillRestriction.SYSTEM_INFO: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.NETWORK_ACCESS,
            ],
            SkillRestriction.DEVELOPER_ASSISTANT: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.FILE_OPERATIONS,
                PermissionLevel.SHELL_COMMANDS,
            ],
            SkillRestriction.SYSTEM_ADMIN: [PermissionLevel.ALL_PERMISSIONS],
        }

    def check_permission(self, tool_name: str) -> bool:
        """
        Check if current skill allows using specified tool

        Args:
            tool_name: Tool name to check

        Returns:
            True if allowed, False otherwise
        """
        if tool_name not in REGISTERED_TOOLS:
            return False

        tool = REGISTERED_TOOLS[tool_name]
        required_permissions = tool.get("permissions", [])
        required_skills = tool.get("skill_types", [])

        # If no skill type specified, check against active skill list
        if not required_skills:
            return True

        # Check specific skill type permissions
        for skill in self.active_skills:
            if skill in required_skills:
                skill_permissions = self.skill_permissions.get(skill, [])
                for required_perm in required_permissions:
                    if required_perm in skill_permissions:
                        return True

        return False

    def is_skill_allowed_for_tool(
        self, skill: SkillRestriction, tool_name: str
    ) -> bool:
        """
        Check if tool is available for specific skill type

        Args:
            skill: Skill type to check
            tool_name: Tool name to check

        Returns:
            True if allowed, False otherwise
        """
        if tool_name not in REGISTERED_TOOLS:
            return False

        tool = REGISTERED_TOOLS[tool_name]
        required_skills = tool.get("skill_types", [])

        # Check if skill type permissions have intersection
        return (
            skill in required_skills or SkillRestriction.ALL_SKILLS in required_skills
        )

    def get_restricted_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tool list available under current restrictions

        Returns:
            Dictionary of available tools
        """
        available_tools = {}

        for tool_name, tool_data in REGISTERED_TOOLS.items():
            # Check any activated skill
            for skill in self.active_skills:
                if self.is_skill_allowed_for_tool(skill, tool_name):
                    available_tools[tool_name] = tool_data
                    break

        return available_tools

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools"""
        return REGISTERED_TOOLS.copy()

    def register_active_skills(self, skills: List[SkillRestriction]):
        """Register active skill permissions"""
        self.active_skills = skills


# Pydantic model examples
class ReadFileModel(BaseModel):
    """File read model"""

    path: str = Field(..., description="File path to read")
    encoding: str = Field(default="utf-8", description="File encoding")


class WriteFileModel(BaseModel):
    """File write model"""

    path: str = Field(..., description="File path to write")
    content: str = Field(..., description="Content to write")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_dirs: bool = Field(default=True, description="Auto-create directories")


class ShellCommandModel(BaseModel):
    """Shell command execution model"""

    command: str = Field(..., description="Shell command to execute")
    confirm: bool = Field(default=True, description="Require user confirmation")
    timeout: int = Field(default=30, description="Timeout in seconds")


class ListFilesModel(BaseModel):
    """File list model"""

    path: str = Field(default=".", description="Directory path to list")
    show_hidden: bool = Field(default=False, description="Show hidden files")
    recursive: bool = Field(default=False, description="Recursive listing")


# Example tool definitions
@function_tool(
    name="read_file",
    description="Read file contents",
    permissions=[PermissionLevel.READ_ONLY],
    skill_types=[
        SkillRestriction.FILE_MANAGER,
        SkillRestriction.DEVELOPER_ASSISTANT,
        SkillRestriction.SYSTEM_ADMIN,
    ],
)
def read_file(model: ReadFileModel) -> str:
    """Enhanced file reading functionality"""
    try:
        with open(model.path, "r", encoding=model.encoding) as f:
            content = f.read()
        return f"✅ Successfully read file {model.path}, content length: {len(content)} characters"
    except FileNotFoundError:
        return f"❌ File not found: {model.path}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


@function_tool(
    name="write_file",
    description="Write file contents",
    permissions=[PermissionLevel.FILE_OPERATIONS],
    skill_types=[SkillRestriction.DEVELOPER_ASSISTANT, SkillRestriction.SYSTEM_ADMIN],
)
def write_file(model: WriteFileModel) -> str:
    """Enhanced file writing functionality"""
    try:
        import os

        if model.create_dirs:
            os.makedirs(os.path.dirname(model.path), exist_ok=True)

        with open(model.path, "w", encoding=model.encoding) as f:
            f.write(model.content)
        return f"✅ Successfully wrote file {model.path}, content length: {len(model.content)} characters"
    except Exception as e:
        return f"❌ Error writing file: {str(e)}"


@function_tool(
    name="execute_shell",
    description="Execute shell commands",
    permissions=[PermissionLevel.SHELL_COMMANDS],
    skill_types=[SkillRestriction.DEVELOPER_ASSISTANT, SkillRestriction.SYSTEM_ADMIN],
)
def execute_shell(model: ShellCommandModel) -> str:
    """Enhanced shell command execution functionality"""
    try:
        import subprocess

        if model.confirm:
            print(f"Confirm execution: {model.command}")
            # In production, add user confirmation here

        result = subprocess.run(
            model.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=model.timeout,
        )

        return f"✅ Command execution completed\nOutput: {result.stdout}\nError: {result.stderr}\nReturn code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"❌ Command execution timeout ({model.timeout} seconds)"
    except Exception as e:
        return f"❌ Command execution failed: {str(e)}"


@function_tool(
    name="list_files",
    description="List files and directories",
    permissions=[PermissionLevel.READ_ONLY],
    skill_types=[
        SkillRestriction.FILE_MANAGER,
        SkillRestriction.DEVELOPER_ASSISTANT,
        SkillRestriction.SYSTEM_ADMIN,
    ],
)
def list_files(model: ListFilesModel) -> str:
    """Enhanced file listing functionality"""
    try:
        import os

        if model.recursive:
            files = []
            for root, dirs, filenames in os.walk(model.path):
                for filename in filenames:
                    if model.show_hidden or not filename.startswith("."):
                        files.append(os.path.join(root, filename))
        else:
            items = os.listdir(model.path)
            files = [
                item for item in items if model.show_hidden or not item.startswith(".")
            ]

        return f"✅ Directory {model.path} contents:\n" + "\n".join(files)
    except Exception as e:
        return f"❌ Failed to list files: {str(e)}"


# Example permission-restricted skills
@function_tool(
    name="safe_file_operations",
    description="Secure file operations (read-only)",
    permissions=[PermissionLevel.READ_ONLY],
    skill_types=[SkillRestriction.FILE_MANAGER, SkillRestriction.CODE_ANALYZER],
)
def safe_file_operations(model: ReadFileModel) -> str:
    """Read-only file analysis functionality"""
    try:
        with open(model.path, "r", encoding=model.encoding) as f:
            content = f.read()

        # Only perform analysis, don't modify files
        lines = content.split("\n")
        return f"📄 File analysis {model.path}:\nLine count: {len(lines)}\nCharacter count: {len(content)}\nIs empty: {'Yes' if not content.strip() else 'No'}"
    except Exception as e:
        return f"❌ File analysis failed: {str(e)}"


def get_all_tools() -> Dict[str, Any]:
    """Get all registered tools"""
    return REGISTERED_TOOLS.copy()


def register_skill_permissions(skills: List[str]) -> PermissionGuard:
    """Register skill permissions for specified skills"""
    skill_restrictions = []
    for skill in skills:
        if skill.endswith("_assistant"):
            skill_name = skill.replace("_assistant", "")
            try:
                skill_restrictions.append(SkillRestriction[skill_name.upper()])
            except KeyError:
                pass
        else:
            try:
                skill_restrictions.append(SkillRestriction[skill.upper()])
            except KeyError:
                pass

    if not skill_restrictions:
        skill_restrictions = [SkillRestriction.ALL_SKILLS]

    return PermissionGuard(skill_restrictions)
