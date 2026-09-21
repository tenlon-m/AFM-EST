#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件差异对比引擎模块
提供多种文件类型的差异对比功能
"""

import os
import difflib
from typing import List, Dict, Tuple, Optional

from core.logger import logger


class TextDiffEngine:
    """
    文本文件差异对比引擎
    使用difflib实现行级和字符级差异检测
    """
    
    def compare(self, file1_path: str, file2_path: str, 
                ignore_whitespace: bool = False, 
                ignore_case: bool = False) -> Dict:
        """
        对比两个文本文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
            ignore_whitespace: 是否忽略空格
            ignore_case: 是否忽略大小写
            
        Returns:
            Dict: 对比结果
        """
        try:
            # 读取文件内容
            with open(file1_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines1 = f.readlines()
            
            with open(file2_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines2 = f.readlines()
            
            # 预处理
            if ignore_case:
                lines1 = [line.lower() for line in lines1]
                lines2 = [line.lower() for line in lines2]
            
            if ignore_whitespace:
                lines1 = [line.strip() for line in lines1]
                lines2 = [line.strip() for line in lines2]
            
            # 生成差异
            differ = difflib.unified_diff(
                lines1, 
                lines2,
                fromfile=os.path.basename(file1_path),
                tofile=os.path.basename(file2_path),
                lineterm=''
            )
            
            diff_lines = list(differ)
            
            # 统计差异
            added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            
            return {
                'success': True,
                'diff_type': 'text',
                'diff_output': ''.join(diff_lines),
                'added_lines': added,
                'removed_lines': removed,
                'total_changes': added + removed,
                'is_identical': added == 0 and removed == 0
            }
            
        except Exception as e:
            logger.debug(f"文本对比失败: {e}")
            return {
                'success': False,
                'error': f'文本对比失败: {str(e)}'
            }


class FolderDiffEngine:
    """
    文件夹差异对比引擎
    对比两个文件夹的文件结构和内容
    """
    
    def compare(self, folder1_path: str, folder2_path: str) -> Dict:
        """
        对比两个文件夹
        
        Args:
            folder1_path: 第一个文件夹路径
            folder2_path: 第二个文件夹路径
            
        Returns:
            Dict: 对比结果
        """
        try:
            # 获取文件夹内容
            files1 = self._get_folder_contents(folder1_path)
            files2 = self._get_folder_contents(folder2_path)
            
            set1 = set(files1)
            set2 = set(files2)
            
            # 计算差异
            only_in_1 = sorted(set1 - set2)
            only_in_2 = sorted(set2 - set1)
            common_files = sorted(set1 & set2)
            
            # 对比共同文件的内容
            modified_files = []
            identical_files = []
            
            for filename in common_files:
                file1 = os.path.join(folder1_path, filename)
                file2 = os.path.join(folder2_path, filename)
                
                # 简单比较文件大小和修改时间
                stat1 = os.stat(file1)
                stat2 = os.stat(file2)
                
                if stat1.st_size != stat2.st_size or stat1.st_mtime != stat2.st_mtime:
                    modified_files.append(filename)
                else:
                    identical_files.append(filename)
            
            return {
                'success': True,
                'diff_type': 'folder',
                'only_in_first': only_in_1,
                'only_in_second': only_in_2,
                'modified': modified_files,
                'identical': identical_files,
                'total_files_1': len(files1),
                'total_files_2': len(files2),
                'summary': {
                    'unique_to_first': len(only_in_1),
                    'unique_to_second': len(only_in_2),
                    'modified': len(modified_files),
                    'identical': len(identical_files)
                }
            }
            
        except Exception as e:
            logger.debug(f"文件夹对比失败: {e}")
            return {
                'success': False,
                'error': f'文件夹对比失败: {str(e)}'
            }
    
    def _get_folder_contents(self, folder_path: str) -> List[str]:
        """
        获取文件夹中的所有文件（相对路径）
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            List[str]: 文件列表
        """
        files = []
        for root, dirs, filenames in os.walk(folder_path):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, folder_path)
                files.append(rel_path)
        return files


class BinaryDiffEngine:
    """
    二进制文件差异对比引擎
    对比二进制文件的字节级差异
    """
    
    def compare(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个二进制文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
            
        Returns:
            Dict: 对比结果
        """
        try:
            # 读取文件内容
            with open(file1_path, 'rb') as f:
                data1 = f.read()
            
            with open(file2_path, 'rb') as f:
                data2 = f.read()
            
            # 基本比较
            size1 = len(data1)
            size2 = len(data2)
            
            if data1 == data2:
                return {
                    'success': True,
                    'diff_type': 'binary',
                    'is_identical': True,
                    'size1': size1,
                    'size2': size2,
                    'different_bytes': 0
                }
            
            # 计算不同字节数
            min_size = min(size1, size2)
            different_bytes = sum(1 for i in range(min_size) if data1[i] != data2[i])
            different_bytes += abs(size1 - size2)  # 加上长度差异
            
            return {
                'success': True,
                'diff_type': 'binary',
                'is_identical': False,
                'size1': size1,
                'size2': size2,
                'different_bytes': different_bytes,
                'similarity': 1.0 - (different_bytes / max(size1, size2)) if max(size1, size2) > 0 else 0
            }
            
        except Exception as e:
            logger.debug(f"二进制对比失败: {e}")
            return {
                'success': False,
                'error': f'二进制对比失败: {str(e)}'
            }


# 全局实例
text_diff_engine = TextDiffEngine()
folder_diff_engine = FolderDiffEngine()
binary_diff_engine = BinaryDiffEngine()
