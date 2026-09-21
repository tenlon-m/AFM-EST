#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行器
运行所有单元测试
"""

import os
import sys
import unittest
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def run_all_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = os.path.dirname(__file__)
    
    suite.addTests(loader.discover(test_dir, pattern='test_*.py'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_name):
    """运行指定测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(test_dir):
        if filename.startswith('test_') and filename.endswith('.py'):
            module_name = filename[:-3]
            module = __import__(module_name)
            
            if hasattr(module, test_name):
                suite.addTests(loader.loadTestsFromTestCase(getattr(module, test_name)))
    
    if not suite.countTestCases():
        print(f"未找到测试: {test_name}")
        return False
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行单元测试')
    parser.add_argument('test_name', nargs='?', default=None,
                        help='指定要运行的测试类名（可选）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("        WJSSDB-QT6 单元测试套件")
    print("=" * 60)
    print()
    
    if args.test_name:
        print(f"运行指定测试: {args.test_name}")
        success = run_specific_test(args.test_name)
    else:
        print("运行所有测试...")
        success = run_all_tests()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败!")
    print("=" * 60)
    
    sys.exit(0 if success else 1)