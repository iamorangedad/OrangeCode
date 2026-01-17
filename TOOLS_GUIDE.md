# 工具注册和权限管理示例

# 如何定义新工具

## 1. 使用装饰器注册工具

```python
from tools import function_tool, PermissionLevel, SkillRestriction
from pydantic import BaseModel, Field

# 定义参数模型
class CustomToolModel(BaseModel):
    param1: str = Field(..., description="参数1描述")
    param2: int = Field(default=10, description="参数2描述")

# 注册工具
@function_tool(
    name="custom_tool",
    description="自定义工具描述",
    permissions=[PermissionLevel.FILE_OPERATIONS],
    skill_types=[SkillRestriction.DEVELOPER_ASSISTANT]
)
def custom_tool(model: CustomToolModel) -> str:
    """工具实现"""
    return f"执行自定义工具，参数1: {model.param1}, 参数2: {model.param2}"
```

## 2. 权限级别说明

- `READ_ONLY`: 只读操作
- `FILE_OPERATIONS`: 文件操作权限
- `SHELL_COMMANDS`: Shell命令执行权限
- `NETWORK_ACCESS`: 网络访问权限
- `SYSTEM_ADMIN`: 系统管理员权限
- `ALL_PERMISSIONS`: 所有权限

## 3. 技能限制说明

- `FILE_MANAGER`: 文件管理技能（只读+文件操作）
- `CODE_ANALYZER`: 代码分析技能（只读+文件操作）
- `SYSTEM_INFO`: 系统信息技能（只读+系统管理）
- `DEVELOPER_ASSISTANT`: 开发助手技能（所有权限）

## 4. 使用示例

### 启动文件管理技能
```bash
orangecode --skills file_manager
```

### 启动代码分析技能（只读权限）
```bash
orangecode --skills code_analyzer
```

### 启动开发助手技能（全权限）
```bash
orangecode --skills developer_assistant
```

### 多技能组合
```bash
orangecode --skills file_manager code_analyzer
```

### 查看可用工具
```bash
orangecode --list-tools
```

### 查看所有技能
```bash
orangecode --list-skills
```

## 5. 权限控制机制

工具定义和权限控制完全解耦：

- **工具定义**: 只需使用 `@function_tool` 装饰器声明所需权限
- **权限守卫**: 自动检查当前技能是否允许使用工具
- **动态过滤**: 根据激活的技能动态过滤可用工具
- **安全防护**: 防止权限不足的工具被误用

## 6. 实际应用场景

### 安全的代码审查工具
```python
@function_tool(
    name="code_review",
    description="安全的代码审查（只读）",
    permissions=[PermissionLevel.READ_ONLY],
    skill_types=[SkillRestriction.CODE_ANALYZER]
)
def safe_code_review(model: FileReadModel) -> str:
    # 只能读取文件，不能修改
    return analyze_code_safety(model.path)
```

### 全功能的开发助手
```python
@function_tool(
    name="full_developer_tools",
    description="完整开发工具集",
    permissions=[PermissionLevel.ALL_PERMISSIONS],
    skill_types=[SkillRestriction.DEVELOPER_ASSISTANT]
)
def full_developer_tools(model: DeveloperToolModel) -> str:
    # 可以执行所有操作
    return execute_full_operations(model)
```

这种设计让工具开发者无需关心权限控制，
守卫系统会统一处理安全检查。