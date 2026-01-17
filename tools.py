"""
工具注册和管理系统
基于装饰器的工具注册，支持动态权限管理
"""

import inspect
from typing import Dict, List, Any, Callable, Optional, Type
from pydantic import BaseModel, Field
from enum import Enum


class PermissionLevel(Enum):
    """权限级别枚举"""

    READ_ONLY = "read_only"  # 只读权限
    FILE_OPERATIONS = "file_ops"  # 文件操作权限
    SHELL_COMMANDS = "shell_cmds"  # Shell命令权限
    NETWORK_ACCESS = "network"  # 网络访问权限
    SYSTEM_ADMIN = "system_admin"  # 系统管理员权限
    ALL_PERMISSIONS = "all"  # 所有权限


class SkillRestriction(Enum):
    """技能限制枚举"""

    FILE_MANAGER = "file_manager"  # 文件管理技能
    CODE_ANALYZER = "code_analyzer"  # 代码分析技能
    SYSTEM_INFO = "system_info"  # 系统信息技能
    DEVELOPER_ASSISTANT = "developer_assistant"  # 开发助手技能
    ALL_SKILLS = "all"  # 所有技能


# 全局工具注册表
_tool_registry: Dict[str, Dict[str, Any]] = {}

# 激活的技能权限
_active_skill_permissions: Dict[str, List[PermissionLevel]] = {}


def function_tool(
    name: str,
    description: str,
    permissions: List[PermissionLevel] = None,
    skill_types: List[SkillRestriction] = None,
):
    """
    工具注册装饰器

    Args:
        name: 工具名称
        description: 工具描述
        permissions: 所需权限列表
        skill_types: 允许的技能类型列表
    """

    def decorator(func: Callable) -> Callable:
        # 获取函数签名和参数模型
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            default_value = (
                param.default if param.default != inspect.Parameter.empty else None
            )

            # 创建Pydantic字段
            if default_value is not None:
                field = Field(
                    default=default_value, description=f"Parameter {param_name}"
                )
            else:
                field = Field(description=f"Parameter {param_name}")

            parameters[param_name] = (param_type, field)

        # 注册工具
        _tool_registry[name] = {
            "function": func,
            "description": description,
            "parameters": parameters,
            "permissions": permissions or [PermissionLevel.ALL_PERMISSIONS],
            "skill_types": skill_types or [SkillRestriction.ALL_SKILLS],
            "name": name,
            "module": func.__module__,
            "docstring": func.__doc__ or "",
        }

        return func

    return decorator


class SkillRestrictionGuard:
    """技能权限守卫"""

    def __init__(self, active_skills: List[str]):
        self.active_skills = active_skills
        self._load_default_permissions()

    def _load_default_permissions(self):
        """加载默认技能权限配置"""
        default_permissions = {
            SkillRestriction.FILE_MANAGER: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.FILE_OPERATIONS,
            ],
            SkillRestriction.CODE_ANALYZER: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.FILE_OPERATIONS,
            ],
            SkillRestriction.SYSTEM_INFO: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.SYSTEM_ADMIN,
            ],
            SkillRestriction.DEVELOPER_ASSISTANT: [
                PermissionLevel.READ_ONLY,
                PermissionLevel.FILE_OPERATIONS,
                PermissionLevel.SHELL_COMMANDS,
                PermissionLevel.NETWORK_ACCESS,
            ],
        }

        for skill in self.active_skills:
            if skill in default_permissions:
                _active_skill_permissions[skill] = default_permissions[skill]
            else:
                _active_skill_permissions[skill] = [PermissionLevel.ALL_PERMISSIONS]

    def can_use_tool(self, tool_name: str, skill_type: str = None) -> bool:
        """检查当前技能是否允许使用指定工具"""
        if tool_name not in _tool_registry:
            return False

        tool_info = _tool_registry[tool_name]

        # 如果没有指定技能类型，使用激活的技能列表检查
        if skill_type is None:
            for skill in self.active_skills:
                if self._check_tool_permission_for_skill(tool_info, skill):
                    return True
            return False

        # 检查特定技能类型的权限
        return self._check_tool_permission_for_skill(tool_info, skill_type)

    def _check_tool_permission_for_skill(
        self, tool_info: Dict[str, Any], skill_type: str
    ) -> bool:
        """检查工具对特定技能类型是否可用"""
        if skill_type not in _active_skill_permissions:
            return False

        allowed_permissions = _active_skill_permissions[skill_type]
        tool_permissions = tool_info["permissions"]

        # 检查权限是否有交集
        return any(perm in allowed_permissions for perm in tool_permissions)

    def get_restricted_tools(self, skill_type: str = None) -> List[str]:
        """获取当前限制下可用的工具列表"""
        available_tools = []

        for tool_name, tool_info in _tool_registry.items():
            if skill_type is None:
                # 检查任何激活的技能
                for skill in self.active_skills:
                    if self._check_tool_permission_for_skill(tool_info, skill):
                        available_tools.append(tool_name)
                        break
            else:
                # 检查特定技能类型
                if self._check_tool_permission_for_skill(tool_info, skill_type):
                    available_tools.append(tool_name)

        return available_tools


def get_all_tools() -> Dict[str, Dict[str, Any]]:
    """获取所有注册的工具"""
    return _tool_registry.copy()


def register_skill_permissions(active_skills: List[str]):
    """注册激活的技能权限"""
    global _active_skill_permissions
    _active_skill_permissions.clear()

    guard = SkillRestrictionGuard(active_skills)
    return guard


# Pydantic模型示例
class FileReadModel(BaseModel):
    """文件读取模型"""

    path: str = Field(..., description="要读取的文件路径")
    encoding: str = Field(default="utf-8", description="文件编码")


class FileWriteModel(BaseModel):
    """文件写入模型"""

    path: str = Field(..., description="要写入的文件路径")
    content: str = Field(..., description="要写入的内容")
    encoding: str = Field(default="utf-8", description="文件编码")
    create_dirs: bool = Field(default=True, description="是否自动创建目录")


class ShellCommandModel(BaseModel):
    """Shell命令执行模型"""

    command: str = Field(..., description="要执行的Shell命令")
    confirm: bool = Field(default=True, description="是否需要用户确认")
    timeout: int = Field(default=30, description="超时时间(秒)")


class ListFilesModel(BaseModel):
    """文件列表模型"""

    path: str = Field(default=".", description="要列出的目录路径")
    show_hidden: bool = Field(default=False, description="是否显示隐藏文件")
    recursive: bool = Field(default=False, description="是否递归列出")


# 示例工具定义
@function_tool(
    name="read_file",
    description="读取文件内容",
    permissions=[PermissionLevel.READ_ONLY, PermissionLevel.FILE_OPERATIONS],
    skill_types=[SkillRestriction.FILE_MANAGER, SkillRestriction.DEVELOPER_ASSISTANT],
)
def enhanced_read_file(model: FileReadModel) -> str:
    """增强的文件读取功能"""
    try:
        with open(model.path, "r", encoding=model.encoding) as f:
            content = f.read()
        return f"✅ 成功读取文件 {model.path}，内容长度: {len(content)} 字符"
    except FileNotFoundError:
        return f"❌ 文件未找到: {model.path}"
    except Exception as e:
        return f"❌ 读取文件时出错: {str(e)}"


@function_tool(
    name="write_file",
    description="写入文件内容",
    permissions=[PermissionLevel.FILE_OPERATIONS],
    skill_types=[SkillRestriction.FILE_MANAGER, SkillRestriction.DEVELOPER_ASSISTANT],
)
def enhanced_write_file(model: FileWriteModel) -> str:
    """增强的文件写入功能"""
    try:
        if model.create_dirs:
            import os

            os.makedirs(os.path.dirname(model.path) or ".", exist_ok=True)

        with open(model.path, "w", encoding=model.encoding) as f:
            f.write(model.content)
        return f"✅ 成功写入文件 {model.path}，内容长度: {len(model.content)} 字符"
    except Exception as e:
        return f"❌ 写入文件时出错: {str(e)}"


@function_tool(
    name="execute_shell",
    description="执行Shell命令",
    permissions=[PermissionLevel.SHELL_COMMANDS],
    skill_types=[SkillRestriction.DEVELOPER_ASSISTANT, SkillRestriction.SYSTEM_ADMIN],
)
def enhanced_shell_command(model: ShellCommandModel) -> str:
    """增强的Shell命令执行功能"""
    try:
        import subprocess

        result = subprocess.run(
            model.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=model.timeout,
        )

        return f"✅ 命令执行完成\n输出: {result.stdout}\n错误: {result.stderr}\n返回码: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"❌ 命令执行超时 ({model.timeout}秒)"
    except Exception as e:
        return f"❌ 命令执行失败: {str(e)}"


@function_tool(
    name="list_files",
    description="列出文件和目录",
    permissions=[PermissionLevel.READ_ONLY, PermissionLevel.FILE_OPERATIONS],
    skill_types=[SkillRestriction.FILE_MANAGER, SkillRestriction.SYSTEM_INFO],
)
def enhanced_list_files(model: ListFilesModel) -> str:
    """增强的文件列表功能"""
    try:
        import os

        if model.recursive:
            files = []
            for root, dirs, filenames in os.walk(model.path):
                if not model.show_hidden:
                    filenames = [f for f in filenames if not f.startswith(".")]
                    dirs = [d for d in dirs if not d.startswith(".")]
                else:
                    filenames = filenames
                    dirs = dirs
                files.extend([os.path.join(root, f) for f in filenames])
                files.extend([os.path.join(root, d + "/") for d in dirs])
        else:
            items = os.listdir(model.path)
            if not model.show_hidden:
                items = [item for item in items if not item.startswith(".")]
            else:
                items = items
            files = [os.path.join(model.path, item) for item in items]

        return f"✅ 目录 {model.path} 内容:\n" + "\n".join(files)
    except Exception as e:
        return f"❌ 列出文件失败: {str(e)}"


# 示例权限受限的技能
@function_tool(
    name="safe_file_operations",
    description="安全的文件操作（只读）",
    permissions=[PermissionLevel.READ_ONLY],
    skill_types=[SkillRestriction.CODE_ANALYZER],
)
def read_only_file_analyzer(model: FileReadModel) -> str:
    """只读文件分析功能"""
    try:
        with open(model.path, "r", encoding=model.encoding) as f:
            content = f.read()

        # 只进行分析，不修改文件
        lines = content.split("\n")
        return f"📄 文件分析 {model.path}:\n行数: {len(lines)}\n字符数: {len(content)}\n是否为空: {'是' if not content.strip() else '否'}"
    except Exception as e:
        return f"❌ 文件分析失败: {str(e)}"
