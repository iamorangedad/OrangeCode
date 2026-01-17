#!/usr/bin/env python3
"""
Convert Chinese comments and docstrings to English in Python files
"""

import ast
import re
import sys
from pathlib import Path


def convert_chinese_in_file(file_path: Path) -> bool:
    """Convert Chinese text to English in a Python file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Chinese to English mapping for common terms
        translations = {
            "工具注册": "Tool registration",
            "权限管理": "Permission management",
            "装饰器": "Decorator",
            "技能限制": "Skill restriction",
            "权限守卫": "Permission guard",
            "项目管理": "Project management",
            "用户输入": "User input",
            "启动加载": "Lazy loading",
            "并发控制": "Concurrency control",
            "流式显示": "Streaming display",
            "ESC键取消": "ESC key cancellation",
            "项目上下文": "Project context",
            "文件操作": "File operations",
            "Shell命令": "Shell commands",
            "网络安全": "Network security",
            "系统管理": "System administration",
        }

        # Replace Chinese in docstrings
        for chinese, english in translations.items():
            content = content.replace(chinese, english)

        # Replace Chinese in comments
        # Pattern to match Chinese characters in comments
        chinese_pattern = re.compile(r"#.*[\u4e00-\u9fff]+")
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            if chinese_pattern.search(line):
                # Try to preserve comment structure while replacing Chinese text
                # Extract the comment prefix
                comment_match = re.match(r"^(\s*#)", line)
                if comment_match:
                    # Replace only the Chinese part
                    chinese_text = re.search(r"[\u4e00-\u9fff]+", line)
                    if chinese_text:
                        english_text = translations.get(
                            chinese_text.group(), chinese_text.group()
                        )
                        new_line = line.replace(chinese_text.group(), english_text)
                        new_lines.append(new_line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        new_content = "\n".join(new_lines)

        # Write back the converted content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function"""
    # Files to process
    files_to_convert = [
        Path("agent_no_rag.py"),
        Path("tools.py"),
        Path("orangecode.py"),
    ]

    converted_count = 0
    for file_path in files_to_convert:
        if file_path.exists():
            print(f"Processing {file_path}...")
            if convert_chinese_in_file(file_path):
                converted_count += 1
                print(f"✅ Converted {file_path}")
            else:
                print(f"❌ Failed to convert {file_path}")
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n📊 Conversion complete: {converted_count} files processed")
    return converted_count > 0


if __name__ == "__main__":
    main()
