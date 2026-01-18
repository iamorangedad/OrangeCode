#!/usr/bin/env python3
"""
Unit tests for utils.py - Utility functions
"""

import pytest
import tempfile
import os
import subprocess
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils import (
    read_file,
    write_file,
    list_files,
    execute_command,
    extract_filename_from_code,
    get_unique_filename,
)


class TestReadFile:
    """Test read_file function"""

    def test_read_existing_file(self):
        """Test reading existing file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_file = f.name

        try:
            result = read_file(temp_file)
            assert "test content" in result
            assert "Error" not in result
        finally:
            os.unlink(temp_file)

    def test_read_nonexistent_file(self):
        """Test reading non-existent file"""
        result = read_file("/tmp/nonexistent_file_12345.txt")
        assert "Error" in result
        assert "not found" in result.lower()

    def test_read_file_with_encoding(self):
        """Test reading file with encoding"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("UTF-8 content")
            temp_file = f.name

        try:
            result = read_file(temp_file)
            assert "UTF-8 content" in result
        finally:
            os.unlink(temp_file)


class TestWriteFile:
    """Test write_file function"""

    def test_write_new_file(self):
        """Test writing new file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            result = write_file(temp_file, "new content")
            assert "Success" in result
            assert "written successfully" in result.lower()

            with open(temp_file, "r") as f:
                content = f.read()
                assert content == "new content"
        finally:
            os.unlink(temp_file)

    def test_write_existing_file(self):
        """Test overwriting existing file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("old content")
            temp_file = f.name

        try:
            result = write_file(temp_file, "new content")
            assert "Success" in result

            with open(temp_file, "r") as f:
                content = f.read()
                assert content == "new content"
        finally:
            os.unlink(temp_file)

    def test_write_file_error(self):
        """Test writing to invalid path"""
        result = write_file("/invalid/path/file.txt", "content")
        assert "Error" in result


class TestListFiles:
    """Test list_files function"""

    def test_list_files_current_directory(self):
        """Test listing files in current directory"""
        result = list_files()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_files_contains_directory_contents(self):
        """Test that listing contains directory contents"""
        result = list_files()
        assert isinstance(eval(result), list) or "[" in result


class TestExecuteCommand:
    """Test execute_command function"""

    def test_execute_successful_command(self):
        """Test executing successful command"""
        result = execute_command("echo 'test'")
        assert "test" in result
        assert "STDOUT:" in result

    def test_execute_command_with_stderr(self):
        """Test executing command with stderr output"""
        result = execute_command("ls /nonexistent_directory_12345")
        assert "STDERR:" in result
        assert "STDOUT:" in result

    def test_execute_timeout_command(self):
        """Test executing command that times out"""
        result = execute_command("sleep 5")  # Command timeout is 3 seconds
        assert "Error" in result
        assert "timed out" in result.lower()

    def test_execute_invalid_command(self):
        """Test executing invalid command"""
        result = execute_command("nonexistent_command_xyz")
        assert "Error" in result or "STDERR:" in result


class TestExtractFilenameFromCode:
    """Test extract_filename_from_code function"""

    def test_python_class_extraction(self):
        """Test Python class filename extraction"""
        code = """
class MyController:
    def __init__(self):
        pass
"""
        filename = extract_filename_from_code(code, "python")
        assert filename == "mycontroller.py"

    def test_python_function_extraction(self):
        """Test Python function filename extraction"""
        code = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
        filename = extract_filename_from_code(code, "python")
        assert filename == "calculate_fibonacci.py"

    def test_flask_app_extraction(self):
        """Test Flask app filename extraction"""
        code = """
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World'
"""
        filename = extract_filename_from_code(code, "python")
        assert filename == "flask_app.py"

    def test_fastapi_app_extraction(self):
        """Test FastAPI app filename extraction"""
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
"""
        filename = extract_filename_from_code(code, "python")
        assert filename == "fastapi_app.py"

    def test_react_component_extraction(self):
        """Test React component filename extraction"""
        code = """
function MyComponent() {
    return <div>Hello</div>;
}
"""
        filename = extract_filename_from_code(code, "javascript")
        assert "mycomponent" in filename.lower()
        assert ".js" in filename or ".jsx" in filename

    def test_javascript_server_extraction(self):
        """Test Express server filename extraction"""
        code = """
const express = require('express');
const app = express();
app.listen(3000);
"""
        filename = extract_filename_from_code(code, "javascript")
        assert filename == "server.js"

    def test_bash_deployment_script_extraction(self):
        """Test bash deployment script filename extraction"""
        code = """
#!/bin/bash
docker-compose up -d
"""
        filename = extract_filename_from_code(code, "bash")
        assert filename == "deploy.sh"

    def test_code_without_patterns(self):
        """Test code without known patterns"""
        code = "some random code without patterns"
        filename = extract_filename_from_code(code, "python")
        assert filename is None


class TestGetUniqueFilename:
    """Test get_unique_filename function"""

    def test_unique_filename_new(self):
        """Test generating unique filename for new file"""
        base_name = "/tmp/test_unique_12345.txt"
        filename = get_unique_filename(base_name)
        assert filename == base_name

    def test_unique_filename_existing(self):
        """Test generating unique filename for existing file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_name = os.path.join(temp_dir, "test.txt")

            # Create base file
            with open(base_name, "w") as f:
                f.write("content")

            # Generate unique filename
            filename = get_unique_filename(base_name)
            assert filename == os.path.join(temp_dir, "test_1.txt")

            # Create first counter
            with open(filename, "w") as f:
                f.write("content1")

            # Generate second unique filename
            filename2 = get_unique_filename(base_name)
            assert filename2 == os.path.join(temp_dir, "test_2.txt")

    def test_multiple_unique_filenames(self):
        """Test generating multiple unique filenames"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_name = os.path.join(temp_dir, "test.txt")

            for i in range(3):
                filename = get_unique_filename(base_name)
                if i == 0:
                    assert filename == base_name
                elif i == 1:
                    assert filename == os.path.join(temp_dir, "test_1.txt")
                elif i == 2:
                    assert filename == os.path.join(temp_dir, "test_2.txt")

                # Create the file to test next iteration
                with open(filename, "w") as f:
                    f.write(f"content_{i}")


class TestUtilityFunctions:
    """Test overall utility functions"""

    def test_read_write_cycle(self):
        """Test read-write cycle"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_file = f.name

        try:
            # Write
            write_result = write_file(temp_file, "cycle test")
            assert "Success" in write_result

            # Read
            read_result = read_file(temp_file)
            assert "cycle test" in read_result
        finally:
            os.unlink(temp_file)

    def test_file_operations_integration(self):
        """Test integrated file operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple files
            for i in range(3):
                filename = os.path.join(temp_dir, f"test_{i}.txt")
                result = write_file(filename, f"content_{i}")
                assert "Success" in result

            # List files
            files_result = list_files()
            assert isinstance(files_result, str)


def run_all_tests():
    """Run all tests"""
    print("🧪 Running Utility Functions Tests")
    print("=" * 50)

    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_all_tests()
