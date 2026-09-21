#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务单元测试
"""

import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.search_service import SearchService


class TestSearchService(unittest.TestCase):
    """搜索服务测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.search_service = SearchService()
        
        self.text_file = os.path.join(self.temp_dir, 'hello.txt')
        with open(self.text_file, 'w', encoding='utf-8') as f:
            f.write('Hello, World! This is a test file for search.')
        
        self.python_file = os.path.join(self.temp_dir, 'test.py')
        with open(self.python_file, 'w', encoding='utf-8') as f:
            f.write('# Python test file\nprint("Hello, Python!")')
        
        self.sub_dir = os.path.join(self.temp_dir, 'subdir')
        os.makedirs(self.sub_dir)
        self.sub_file = os.path.join(self.sub_dir, 'nested.txt')
        with open(self.sub_file, 'w', encoding='utf-8') as f:
            f.write('Nested file content for search testing.')
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_search_in_directory(self):
        """测试目录搜索"""
        results = self.search_service.search_in_directory(self.temp_dir, 'hello')
        self.assertGreater(len(results), 0)
    
    def test_search_by_content(self):
        """测试按内容搜索"""
        results = self.search_service.search_by_content(self.temp_dir, 'test')
        self.assertGreater(len(results), 0)
    
    def test_search_empty_pattern(self):
        """测试空搜索模式"""
        results = self.search_service.search_in_directory(self.temp_dir, '')
        self.assertGreater(len(results), 0)
    
    def test_search_nonexistent_directory(self):
        """测试搜索不存在的目录"""
        results = self.search_service.search_in_directory('/nonexistent/path', 'test')
        self.assertEqual(len(results), 0)
    
    def test_search_with_page(self):
        """测试分页搜索"""
        results = self.search_service.search_in_directory(self.temp_dir, 'test', page=1, page_size=10)
        self.assertIsInstance(results, dict)
        self.assertIn('results', results)
        self.assertIn('total', results)


if __name__ == '__main__':
    unittest.main()