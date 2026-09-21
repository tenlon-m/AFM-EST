#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AFM-EST 部署脚本
用于打包应用程序、生成安装程序和创建便携版
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


class DeploymentManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.dist_dir = project_root / "dist"
        self.build_dir = project_root / "build"
        self.version = self._get_version()
    
    def _get_version(self) -> str:
        version_file = self.project_root / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "1.0.0"
    
    def clean(self):
        print("清理构建目录...")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        print("清理完成")
    
    def build_executable(self, platform: str = "windows"):
        print(f"构建可执行文件 (平台: {platform})...")
        
        self.dist_dir.mkdir(exist_ok=True)
        self.build_dir.mkdir(exist_ok=True)
        
        main_script = self.project_root / "src" / "main.py"
        
        if platform == "windows":
            cmd = [
                "pyinstaller",
                "--name=AFM-EST",
                f"--version-file={self.project_root / 'version_info.txt'}",
                "--windowed",
                "--onefile",
                "--icon=resources/icon.ico",
                f"--distpath={self.dist_dir}",
                f"--workpath={self.build_dir}",
                str(main_script)
            ]
        else:
            cmd = [
                "pyinstaller",
                "--name=AFM-EST",
                "--windowed",
                "--onefile",
                f"--distpath={self.dist_dir}",
                f"--workpath={self.build_dir}",
                str(main_script)
            ]
        
        subprocess.run(cmd, check=True)
        print("可执行文件构建完成")
    
    def create_portable(self):
        print("创建便携版...")
        
        portable_dir = self.dist_dir / f"AFM-EST-{self.version}-Portable"
        portable_dir.mkdir(exist_ok=True)
        
        src_dir = self.project_root / "src"
        shutil.copytree(src_dir, portable_dir / "src", dirs_exist_ok=True)
        
        resources_dir = self.project_root / "resources"
        if resources_dir.exists():
            shutil.copytree(resources_dir, portable_dir / "resources", dirs_exist_ok=True)
        
        config_dir = self.project_root / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, portable_dir / "config", dirs_exist_ok=True)
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            shutil.copy(requirements_file, portable_dir / "requirements.txt")
        
        launcher_script = portable_dir / "launch.py"
        launcher_script.write_text("""#!/usr/bin/env python3
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

from main import main

if __name__ == '__main__':
    main()
""")
        
        readme_file = portable_dir / "README.txt"
        readme_file.write_text(f"""AFM-EST 文件管理器 便携版 v{self.version}

使用方法:
1. 确保已安装 Python 3.9 或更高版本
2. 安装依赖: pip install -r requirements.txt
3. 运行: python launch.py

系统要求:
- Python 3.9+
- PySide6
- psutil

更多信息请访问: https://github.com/afm-est/afm-est
""")
        
        archive_name = f"AFM-EST-{self.version}-Portable"
        shutil.make_archive(
            str(self.dist_dir / archive_name),
            'zip',
            self.dist_dir,
            portable_dir.name
        )
        
        print(f"便携版创建完成: {archive_name}.zip")
    
    def create_installer(self, platform: str = "windows"):
        print(f"创建安装程序 (平台: {platform})...")
        
        if platform == "windows":
            installer_script = self.project_root / "scripts" / "installer.nsi"
            if installer_script.exists():
                subprocess.run(["makensis", str(installer_script)], check=True)
                print("Windows安装程序创建完成")
            else:
                print("警告: 未找到NSIS安装脚本")
        else:
            print("Linux平台建议使用AppImage或Snap打包")
    
    def package_dependencies(self):
        print("打包依赖...")
        
        deps_dir = self.dist_dir / "dependencies"
        deps_dir.mkdir(exist_ok=True)
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "-r", str(requirements_file),
                "-d", str(deps_dir)
            ]
            subprocess.run(cmd, check=True)
            print(f"依赖包下载完成: {deps_dir}")
        else:
            print("警告: 未找到requirements.txt")
    
    def generate_checksums(self):
        print("生成校验和...")
        
        import hashlib
        
        checksums_file = self.dist_dir / "checksums.txt"
        
        with open(checksums_file, 'w') as f:
            for file_path in self.dist_dir.rglob("*"):
                if file_path.is_file() and file_path != checksums_file:
                    sha256 = hashlib.sha256()
                    with open(file_path, 'rb') as fp:
                        for chunk in iter(lambda: fp.read(4096), b''):
                            sha256.update(chunk)
                    
                    relative_path = file_path.relative_to(self.dist_dir)
                    f.write(f"{sha256.hexdigest()}  {relative_path}\n")
        
        print(f"校验和文件生成完成: {checksums_file}")


def main():
    parser = argparse.ArgumentParser(description="AFM-EST 部署脚本")
    parser.add_argument("--clean", action="store_true", help="清理构建目录")
    parser.add_argument("--build", action="store_true", help="构建可执行文件")
    parser.add_argument("--portable", action="store_true", help="创建便携版")
    parser.add_argument("--installer", action="store_true", help="创建安装程序")
    parser.add_argument("--deps", action="store_true", help="打包依赖")
    parser.add_argument("--all", action="store_true", help="执行所有构建步骤")
    parser.add_argument("--platform", default="windows", choices=["windows", "linux"], help="目标平台")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    manager = DeploymentManager(project_root)
    
    if args.all:
        args.clean = True
        args.build = True
        args.portable = True
        args.installer = True
        args.deps = True
    
    try:
        if args.clean:
            manager.clean()
        
        if args.build:
            manager.build_executable(args.platform)
        
        if args.portable:
            manager.create_portable()
        
        if args.installer:
            manager.create_installer(args.platform)
        
        if args.deps:
            manager.package_dependencies()
        
        manager.generate_checksums()
        
        print("\n部署完成!")
        
    except Exception as e:
        print(f"\n部署失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()