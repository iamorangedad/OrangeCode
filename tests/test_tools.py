#!/usr/bin/env python3
"""
Unit tests for tools.py - Tool registration and permission management
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    function_tool,
    PermissionLevel,
    SkillRestriction,
    PermissionGuard,
    get_all_tools,
    register_skill_permissions,
    ReadFileModel,
    WriteFileModel,
    ShellCommandModel,
    ListFilesModel,
)


class TestPermissionLevel:
    """Test PermissionLevel enum"""

    def test_permission_level_values(self):
        """Test that all permission levels are defined"""
        assert PermissionLevel.READ_ONLY.value == "read_only"
        assert PermissionLevel.FILE_OPERATIONS.value == "file_ops"
        assert PermissionLevel.SHELL_COMMANDS.value == "shell_cmds"
        assert PermissionLevel.NETWORK_ACCESS.value == "network"
        assert PermissionLevel.SYSTEM_ADMIN.value == "system_admin"
        assert PermissionLevel.ALL_PERMISSIONS.value == "all"

    def test_permission_level_count(self):
        """Test that there are 6 permission levels"""
        assert len(PermissionLevel) == 6


class TestSkillRestriction:
    """Test SkillRestriction enum"""

    def test_skill_restriction_values(self):
        """Test that all skill restrictions are defined"""
        assert SkillRestriction.FILE_MANAGER.value == "file_manager"
        assert SkillRestriction.CODE_ANALYZER.value == "code_analyzer"
        assert SkillRestriction.SYSTEM_INFO.value == "system_info"
        assert SkillRestriction.DEVELOPER_ASSISTANT.value == "developer_assistant"
        assert SkillRestriction.SYSTEM_ADMIN.value == "system_admin"
        assert SkillRestriction.ALL_SKILLS.value == "all"

    def test_skill_restriction_count(self):
        """Test that there are 6 skill restrictions"""
        assert len(SkillRestriction) == 6


class TestFunctionTool:
    """Test @function_tool decorator"""

    def test_basic_tool_registration(self):
        """Test basic tool registration"""

        @function_tool(
            name="test_tool",
            description="Test tool description",
            permissions=[PermissionLevel.READ_ONLY],
        )
        def test_function():
            return "test result"

        tools = get_all_tools()
        assert "test_tool" in tools
        assert tools["test_tool"]["name"] == "test_tool"
        assert tools["test_tool"]["description"] == "Test tool description"
        assert PermissionLevel.READ_ONLY in tools["test_tool"]["permissions"]

    def test_tool_auto_naming(self):
        """Test automatic tool naming"""

        @function_tool(description="Auto-named tool")
        def my_custom_function():
            return "result"

        tools = get_all_tools()
        assert "my_custom_function" in tools

    def test_tool_with_skill_restrictions(self):
        """Test tool with skill restrictions"""

        @function_tool(
            name="dev_tool",
            permissions=[PermissionLevel.FILE_OPERATIONS],
            skill_types=[SkillRestriction.DEVELOPER_ASSISTANT],
        )
        def dev_function():
            return "dev result"

        tools = get_all_tools()
        assert "dev_tool" in tools
        assert SkillRestriction.DEVELOPER_ASSISTANT in tools["dev_tool"]["skill_types"]


class TestPermissionGuard:
    """Test PermissionGuard class"""

    def test_permission_guard_initialization(self):
        """Test permission guard initialization"""
        guard = PermissionGuard([SkillRestriction.DEVELOPER_ASSISTANT])
        assert SkillRestriction.DEVELOPER_ASSISTANT in guard.active_skills

    def test_permission_guard_default_skills(self):
        """Test permission guard with default skills"""
        guard = PermissionGuard()
        assert len(guard.active_skills) > 0

    def test_check_permission_allowed_tool(self):
        """Test permission check for allowed tool"""
        guard = PermissionGuard([SkillRestriction.DEVELOPER_ASSISTANT])
        result = guard.check_permission("read_file")
        assert result is True

    def test_check_permission_restricted_tool(self):
        """Test permission check for restricted tool"""
        guard = PermissionGuard([SkillRestriction.CODE_ANALYZER])
        result = guard.check_permission("write_file")
        assert result is False

    def test_get_restricted_tools(self):
        """Test getting restricted tools"""
        guard = PermissionGuard([SkillRestriction.DEVELOPER_ASSISTANT])
        tools = guard.get_restricted_tools()
        assert len(tools) > 0
        assert "read_file" in tools
        assert "write_file" in tools

    def test_register_active_skills(self):
        """Test registering active skills"""
        guard = PermissionGuard()
        guard.register_active_skills([SkillRestriction.SYSTEM_ADMIN])
        assert SkillRestriction.SYSTEM_ADMIN in guard.active_skills


class TestBuiltInTools:
    """Test built-in tools"""

    def test_read_file_tool_exists(self):
        """Test read_file tool is registered"""
        tools = get_all_tools()
        assert "read_file" in tools
        assert "Read file contents" in tools["read_file"]["description"]

    def test_write_file_tool_exists(self):
        """Test write_file tool is registered"""
        tools = get_all_tools()
        assert "write_file" in tools
        assert "Write file contents" in tools["write_file"]["description"]

    def test_execute_shell_tool_exists(self):
        """Test execute_shell tool is registered"""
        tools = get_all_tools()
        assert "execute_shell" in tools
        assert "Execute shell commands" in tools["execute_shell"]["description"]

    def test_list_files_tool_exists(self):
        """Test list_files tool is registered"""
        tools = get_all_tools()
        assert "list_files" in tools
        assert "List files and directories" in tools["list_files"]["description"]

    def test_safe_file_operations_tool_exists(self):
        """Test safe_file_operations tool is registered"""
        tools = get_all_tools()
        assert "safe_file_operations" in tools
        assert "Secure file operations" in tools["safe_file_operations"]["description"]


class TestToolModels:
    """Test Pydantic models for tools"""

    def test_read_file_model(self):
        """Test ReadFileModel"""
        model = ReadFileModel(path="/tmp/test.txt", encoding="utf-8")
        assert model.path == "/tmp/test.txt"
        assert model.encoding == "utf-8"

    def test_write_file_model(self):
        """Test WriteFileModel"""
        model = WriteFileModel(
            path="/tmp/test.txt", content="test content", create_dirs=True
        )
        assert model.path == "/tmp/test.txt"
        assert model.content == "test content"
        assert model.create_dirs is True

    def test_shell_command_model(self):
        """Test ShellCommandModel"""
        model = ShellCommandModel(command="ls -la", confirm=False, timeout=10)
        assert model.command == "ls -la"
        assert model.confirm is False
        assert model.timeout == 10

    def test_list_files_model(self):
        """Test ListFilesModel"""
        model = ListFilesModel(path="/tmp", show_hidden=True, recursive=False)
        assert model.path == "/tmp"
        assert model.show_hidden is True
        assert model.recursive is False


class TestRegisterSkillPermissions:
    """Test register_skill_permissions function"""

    def test_register_developer_skills(self):
        """Test registering developer skills"""
        guard = register_skill_permissions(["developer_assistant"])
        assert len(guard.active_skills) > 0

    def test_register_system_admin_skills(self):
        """Test registering system admin skills"""
        guard = register_skill_permissions(["system_admin"])
        assert SkillRestriction.SYSTEM_ADMIN in guard.active_skills

    def test_register_invalid_skill(self):
        """Test registering invalid skill falls back to default"""
        guard = register_skill_permissions(["invalid_skill"])
        assert len(guard.active_skills) > 0


def run_all_tests():
    """Run all tests"""
    print("🧪 Running Tool Registration and Permission Tests")
    print("=" * 50)

    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_all_tests()
