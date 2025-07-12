#!/usr/bin/env python3
"""
Smart-0DTE-System Test Runner

Comprehensive test runner for the Smart-0DTE-System with support for
different test types, coverage reporting, and performance testing.
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestRunner:
    """Comprehensive test runner for Smart-0DTE-System."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.coverage_threshold = 80.0
        
    def run_unit_tests(self, verbose: bool = False) -> bool:
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        
        cmd = [
            'python', '-m', 'pytest',
            str(self.test_dir / 'unit'),
            '-m', 'unit',
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def run_integration_tests(self, verbose: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        
        cmd = [
            'python', '-m', 'pytest',
            str(self.test_dir / 'integration'),
            '-m', 'integration',
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def run_e2e_tests(self, verbose: bool = False) -> bool:
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        
        cmd = [
            'python', '-m', 'pytest',
            str(self.test_dir / 'e2e'),
            '-m', 'e2e',
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def run_all_tests(self, verbose: bool = False) -> bool:
        """Run all tests."""
        print("🚀 Running All Tests...")
        
        cmd = [
            'python', '-m', 'pytest',
            str(self.test_dir),
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def run_with_coverage(self, test_type: str = 'all', verbose: bool = False) -> bool:
        """Run tests with coverage reporting."""
        print(f"📊 Running {test_type.title()} Tests with Coverage...")
        
        cmd = [
            'python', '-m', 'pytest',
            '--cov=app',
            '--cov-report=html',
            '--cov-report=term-missing',
            f'--cov-fail-under={self.coverage_threshold}',
            '--tb=short'
        ]
        
        if test_type == 'unit':
            cmd.extend([str(self.test_dir / 'unit'), '-m', 'unit'])
        elif test_type == 'integration':
            cmd.extend([str(self.test_dir / 'integration'), '-m', 'integration'])
        elif test_type == 'e2e':
            cmd.extend([str(self.test_dir / 'e2e'), '-m', 'e2e'])
        else:
            cmd.append(str(self.test_dir))
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        
        if result.returncode == 0:
            print(f"✅ Coverage report generated in {self.project_root}/htmlcov/")
        
        return result.returncode == 0
    
    def run_performance_tests(self, verbose: bool = False) -> bool:
        """Run performance tests."""
        print("⚡ Running Performance Tests...")
        
        cmd = [
            'python', '-m', 'pytest',
            str(self.test_dir),
            '-m', 'slow',
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> bool:
        """Run a specific test file or test function."""
        print(f"🎯 Running Specific Test: {test_path}")
        
        cmd = [
            'python', '-m', 'pytest',
            test_path,
            '--tb=short'
        ]
        
        if verbose:
            cmd.append('-v')
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode == 0
    
    def validate_test_environment(self) -> bool:
        """Validate that the test environment is properly set up."""
        print("🔍 Validating Test Environment...")
        
        # Check if pytest is installed
        try:
            import pytest
            print(f"✅ pytest {pytest.__version__} is installed")
        except ImportError:
            print("❌ pytest is not installed. Run: pip install pytest")
            return False
        
        # Check if coverage is installed
        try:
            import coverage
            print(f"✅ coverage {coverage.__version__} is installed")
        except ImportError:
            print("❌ coverage is not installed. Run: pip install pytest-cov")
            return False
        
        # Check if test dependencies are available
        required_modules = [
            'asyncio', 'unittest.mock', 'pandas', 'numpy'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
                print(f"✅ {module} is available")
            except ImportError:
                print(f"❌ {module} is not available")
                return False
        
        # Check test directory structure
        required_dirs = ['unit', 'integration', 'e2e']
        for dir_name in required_dirs:
            test_dir = self.test_dir / dir_name
            if test_dir.exists():
                print(f"✅ {dir_name} test directory exists")
            else:
                print(f"❌ {dir_name} test directory missing")
                return False
        
        print("✅ Test environment validation passed")
        return True
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report."""
        print("📋 Generating Test Report...")
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_results': {},
            'coverage': {},
            'summary': {}
        }
        
        # Run tests and collect results
        test_types = ['unit', 'integration', 'e2e']
        
        for test_type in test_types:
            print(f"Running {test_type} tests for report...")
            
            if test_type == 'unit':
                success = self.run_unit_tests()
            elif test_type == 'integration':
                success = self.run_integration_tests()
            else:
                success = self.run_e2e_tests()
            
            report['test_results'][test_type] = {
                'passed': success,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Generate summary
        total_tests = len(test_types)
        passed_tests = sum(1 for result in report['test_results'].values() if result['passed'])
        
        report['summary'] = {
            'total_test_suites': total_tests,
            'passed_test_suites': passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'overall_status': 'PASSED' if passed_tests == total_tests else 'FAILED'
        }
        
        return report
    
    def print_test_summary(self, report: Dict[str, Any]) -> None:
        """Print a formatted test summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Status: {report['summary']['overall_status']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")
        print()
        
        print("Test Results:")
        for test_type, result in report['test_results'].items():
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            print(f"  {test_type.title()}: {status}")
        
        print("\n" + "="*60)


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description='Smart-0DTE-System Test Runner')
    
    parser.add_argument(
        'test_type',
        choices=['unit', 'integration', 'e2e', 'all', 'performance', 'validate'],
        nargs='?',
        default='all',
        help='Type of tests to run'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run tests with coverage reporting'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--specific',
        type=str,
        help='Run a specific test file or function'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate comprehensive test report'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Validate environment first
    if not runner.validate_test_environment():
        print("❌ Test environment validation failed")
        sys.exit(1)
    
    success = True
    
    if args.specific:
        success = runner.run_specific_test(args.specific, args.verbose)
    elif args.report:
        report = runner.generate_test_report()
        runner.print_test_summary(report)
        success = report['summary']['overall_status'] == 'PASSED'
    elif args.test_type == 'validate':
        # Already validated above
        pass
    elif args.coverage:
        success = runner.run_with_coverage(args.test_type, args.verbose)
    else:
        if args.test_type == 'unit':
            success = runner.run_unit_tests(args.verbose)
        elif args.test_type == 'integration':
            success = runner.run_integration_tests(args.verbose)
        elif args.test_type == 'e2e':
            success = runner.run_e2e_tests(args.verbose)
        elif args.test_type == 'performance':
            success = runner.run_performance_tests(args.verbose)
        else:  # all
            success = runner.run_all_tests(args.verbose)
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()

