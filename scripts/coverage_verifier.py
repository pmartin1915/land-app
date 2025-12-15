"""
Comprehensive Test Coverage Verifier for Alabama Auction Watcher.

This module provides advanced test coverage analysis and verification to ensure
>95% coverage across all core modules. Includes AI-friendly reporting, gap analysis,
and actionable recommendations for improving test coverage.

Features:
- Comprehensive coverage analysis across all test types
- Line-by-line coverage gap identification
- AI-friendly structured reporting
- Coverage trend analysis and recommendations
- Integration with CI/CD pipelines
- Automated coverage verification and enforcement
"""

import ast
import json
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Tuple
import coverage

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger


@dataclass
class ModuleCoverage:
    """Coverage information for a single module."""
    module_name: str
    file_path: str
    total_lines: int
    covered_lines: int
    missing_lines: List[int]
    excluded_lines: List[int]
    coverage_percentage: float
    complexity_score: float
    critical_functions: List[str]
    test_files_covering: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageReport:
    """Comprehensive coverage report."""
    timestamp: float
    overall_coverage: float
    target_coverage: float
    meets_threshold: bool
    total_modules: int
    modules_above_threshold: int
    modules_below_threshold: int
    module_coverage: List[ModuleCoverage]
    coverage_gaps: List[Dict[str, Any]]
    recommendations: List[str]
    ai_analysis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'module_coverage': [module.to_dict() for module in self.module_coverage]
        }


class CodeAnalyzer:
    """Analyzes code complexity and critical functions."""

    def __init__(self):
        """Initialize the code analyzer."""
        self.logger = get_ai_logger(__name__)

    def analyze_module(self, file_path: Path) -> Tuple[float, List[str]]:
        """Analyze module complexity and identify critical functions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            complexity_score = self._calculate_complexity(tree)
            critical_functions = self._identify_critical_functions(tree)

            return complexity_score, critical_functions

        except Exception as e:
            self.logger.log_error_with_ai_context(e, f"analyze_module_{file_path}")
            return 0.0, []

    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate cyclomatic complexity of the module."""
        complexity = 0

        for node in ast.walk(tree):
            # Count decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        # Normalize by number of functions
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        function_count = len(functions) or 1

        return complexity / function_count

    def _identify_critical_functions(self, tree: ast.AST) -> List[str]:
        """Identify critical functions that require high test coverage."""
        critical_functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name

                # Check for critical indicators
                is_critical = False

                # Public API functions (not starting with _)
                if not function_name.startswith('_'):
                    is_critical = True

                # Functions with error handling
                if any(isinstance(n, ast.ExceptHandler) for n in ast.walk(node)):
                    is_critical = True

                # Functions with complex logic
                decision_points = len([
                    n for n in ast.walk(node)
                    if isinstance(n, (ast.If, ast.While, ast.For))
                ])
                if decision_points > 2:
                    is_critical = True

                # Functions that handle data processing
                if any(keyword in function_name.lower() for keyword in
                      ['process', 'parse', 'calculate', 'validate', 'transform']):
                    is_critical = True

                if is_critical:
                    critical_functions.append(function_name)

        return critical_functions


class CoverageCollector:
    """Collects coverage data from various test execution runs."""

    def __init__(self):
        """Initialize the coverage collector."""
        self.logger = get_ai_logger(__name__)
        self.coverage_data = {}

    def run_coverage_analysis(self, test_pattern: str = "tests/") -> Dict[str, Any]:
        """Run comprehensive coverage analysis."""
        self.logger.info("Starting comprehensive coverage analysis")

        # Prepare coverage configuration
        cov = coverage.Coverage(
            source=['scripts', 'config', 'streamlit_app'],
            omit=[
                '*/tests/*',
                '*/test_*.py',
                '*/__pycache__/*',
                '*/.*'
            ]
        )

        try:
            # Start coverage collection
            cov.start()

            # Run tests with coverage
            self._run_tests_with_coverage(test_pattern)

            # Stop coverage collection
            cov.stop()
            cov.save()

            # Generate coverage report
            coverage_data = self._extract_coverage_data(cov)

            self.logger.log_performance(
                "coverage_analysis",
                duration_ms=0,  # Quick operation
                modules_analyzed=len(coverage_data.get('modules', []))
            )

            return coverage_data

        except Exception as e:
            self.logger.log_error_with_ai_context(e, "coverage_analysis")
            raise

    def _run_tests_with_coverage(self, test_pattern: str) -> None:
        """Run tests while collecting coverage data."""
        # Import modules to ensure they're included in coverage
        self._import_target_modules()

        # Run different test suites
        test_commands = [
            ['python', '-m', 'pytest', 'tests/unit/', '-v', '--tb=short'],
            ['python', '-m', 'pytest', 'tests/integration/', '-v', '--tb=short'],
            ['python', '-m', 'pytest', 'tests/e2e/', '-v', '--tb=short'],
        ]

        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minutes per test suite
                    cwd=project_root
                )

                if result.returncode != 0:
                    self.logger.warning(f"Test command failed: {' '.join(cmd)}")

            except subprocess.TimeoutExpired:
                self.logger.warning(f"Test command timed out: {' '.join(cmd)}")
            except Exception as e:
                self.logger.log_error_with_ai_context(e, f"run_test_command_{cmd[3]}")

    def _import_target_modules(self) -> None:
        """Import target modules to ensure they're tracked by coverage."""
        target_modules = [
            'scripts.parser',
            'scripts.scraper',
            'scripts.utils',
            'scripts.exceptions',
            'scripts.ai_exceptions',
            'config.settings',
            'config.logging_config',
            'config.ai_logging',
            'config.ai_diagnostics'
        ]

        for module_name in target_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                self.logger.warning(f"Could not import {module_name}: {e}")

    def _extract_coverage_data(self, cov: coverage.Coverage) -> Dict[str, Any]:
        """Extract detailed coverage data from coverage object."""
        coverage_data = {
            'overall_coverage': 0.0,
            'modules': [],
            'summary': {
                'total_lines': 0,
                'covered_lines': 0,
                'missing_lines': 0
            }
        }

        # Get coverage data
        try:
            # Generate XML report for detailed analysis
            xml_file = project_root / 'coverage.xml'
            cov.xml_report(outfile=str(xml_file))

            # Generate HTML report for human consumption
            html_dir = project_root / 'htmlcov'
            cov.html_report(directory=str(html_dir))

            # Extract data from coverage object
            analysis_data = cov.get_data()

            total_covered = 0
            total_lines = 0

            for filename in analysis_data.measured_files():
                if self._should_include_file(Path(filename)):
                    file_data = cov.analysis2(filename)

                    lines_covered = len(file_data[1])  # executed lines
                    lines_missing = len(file_data[2])  # missing lines
                    total_file_lines = lines_covered + lines_missing

                    if total_file_lines > 0:
                        coverage_data['modules'].append({
                            'file': filename,
                            'lines_covered': lines_covered,
                            'lines_missing': lines_missing,
                            'total_lines': total_file_lines,
                            'coverage': (lines_covered / total_file_lines) * 100,
                            'missing_lines': list(file_data[2])
                        })

                        total_covered += lines_covered
                        total_lines += total_file_lines

            # Calculate overall coverage
            if total_lines > 0:
                coverage_data['overall_coverage'] = (total_covered / total_lines) * 100

            coverage_data['summary'] = {
                'total_lines': total_lines,
                'covered_lines': total_covered,
                'missing_lines': total_lines - total_covered
            }

        except Exception as e:
            self.logger.log_error_with_ai_context(e, "extract_coverage_data")

        return coverage_data

    def _should_include_file(self, file_path: Path) -> bool:
        """Determine if a file should be included in coverage analysis."""
        # Include files from core modules
        include_patterns = ['scripts/', 'config/', 'streamlit_app/']
        exclude_patterns = ['test_', '__pycache__', '.pyc', '/.']

        file_str = str(file_path)

        # Check if file is in included directories
        if not any(pattern in file_str for pattern in include_patterns):
            return False

        # Check if file should be excluded
        if any(pattern in file_str for pattern in exclude_patterns):
            return False

        return True


class CoverageVerifier:
    """Main coverage verification system."""

    def __init__(self, target_coverage: float = 95.0):
        """Initialize the coverage verifier."""
        self.target_coverage = target_coverage
        self.logger = get_ai_logger(__name__)
        self.code_analyzer = CodeAnalyzer()
        self.coverage_collector = CoverageCollector()

    def verify_coverage(self) -> CoverageReport:
        """Perform comprehensive coverage verification."""
        self.logger.info(f"Starting coverage verification (target: {self.target_coverage}%)")

        start_time = time.time()

        # Collect coverage data
        coverage_data = self.coverage_collector.run_coverage_analysis()

        # Analyze each module
        module_coverage = self._analyze_module_coverage(coverage_data)

        # Calculate overall metrics
        overall_coverage = coverage_data.get('overall_coverage', 0.0)
        meets_threshold = overall_coverage >= self.target_coverage

        modules_above = sum(1 for m in module_coverage if m.coverage_percentage >= self.target_coverage)
        modules_below = len(module_coverage) - modules_above

        # Identify coverage gaps
        coverage_gaps = self._identify_coverage_gaps(module_coverage)

        # Generate recommendations
        recommendations = self._generate_recommendations(module_coverage, coverage_gaps)

        # AI analysis
        ai_analysis = self._generate_ai_analysis(module_coverage, overall_coverage)

        # Create comprehensive report
        report = CoverageReport(
            timestamp=time.time(),
            overall_coverage=overall_coverage,
            target_coverage=self.target_coverage,
            meets_threshold=meets_threshold,
            total_modules=len(module_coverage),
            modules_above_threshold=modules_above,
            modules_below_threshold=modules_below,
            module_coverage=module_coverage,
            coverage_gaps=coverage_gaps,
            recommendations=recommendations,
            ai_analysis=ai_analysis
        )

        execution_time = time.time() - start_time

        self.logger.log_performance(
            "coverage_verification",
            duration_ms=execution_time * 1000,
            overall_coverage=overall_coverage,
            modules_analyzed=len(module_coverage),
            meets_threshold=meets_threshold
        )

        return report

    def _analyze_module_coverage(self, coverage_data: Dict[str, Any]) -> List[ModuleCoverage]:
        """Analyze coverage for each module."""
        module_coverage = []

        for module_data in coverage_data.get('modules', []):
            file_path = Path(module_data['file'])

            # Get code analysis
            complexity_score, critical_functions = self.code_analyzer.analyze_module(file_path)

            # Find test files covering this module
            test_files = self._find_covering_test_files(file_path)

            module_info = ModuleCoverage(
                module_name=file_path.stem,
                file_path=str(file_path),
                total_lines=module_data.get('total_lines', 0),
                covered_lines=module_data.get('lines_covered', 0),
                missing_lines=module_data.get('missing_lines', []),
                excluded_lines=[],  # Could be extracted from coverage data
                coverage_percentage=module_data.get('coverage', 0.0),
                complexity_score=complexity_score,
                critical_functions=critical_functions,
                test_files_covering=test_files
            )

            module_coverage.append(module_info)

        return module_coverage

    def _find_covering_test_files(self, module_path: Path) -> List[str]:
        """Find test files that cover a specific module."""
        test_files = []

        # Search for corresponding test files
        module_name = module_path.stem

        test_patterns = [
            f"tests/unit/test_{module_name}.py",
            f"tests/integration/test_{module_name}*.py",
            f"tests/e2e/test_*{module_name}*.py"
        ]

        for pattern in test_patterns:
            test_path = project_root / pattern
            if '*' in pattern:
                # Handle glob patterns
                import glob
                matches = glob.glob(str(project_root / pattern))
                test_files.extend([str(Path(m).relative_to(project_root)) for m in matches])
            elif test_path.exists():
                test_files.append(str(test_path.relative_to(project_root)))

        return test_files

    def _identify_coverage_gaps(self, module_coverage: List[ModuleCoverage]) -> List[Dict[str, Any]]:
        """Identify specific coverage gaps that need attention."""
        gaps = []

        for module in module_coverage:
            if module.coverage_percentage < self.target_coverage:
                gap_info = {
                    'module': module.module_name,
                    'current_coverage': module.coverage_percentage,
                    'target_coverage': self.target_coverage,
                    'coverage_deficit': self.target_coverage - module.coverage_percentage,
                    'missing_lines_count': len(module.missing_lines),
                    'missing_lines': module.missing_lines[:10],  # First 10 missing lines
                    'critical_functions_uncovered': [],
                    'test_files': module.test_files_covering,
                    'complexity_score': module.complexity_score,
                    'priority': self._calculate_gap_priority(module)
                }

                # Check if critical functions are uncovered
                # This would require more detailed analysis of which specific functions are covered
                gap_info['critical_functions_uncovered'] = module.critical_functions[:5]  # Simplified

                gaps.append(gap_info)

        # Sort by priority (highest first)
        gaps.sort(key=lambda x: x['priority'], reverse=True)

        return gaps

    def _calculate_gap_priority(self, module: ModuleCoverage) -> float:
        """Calculate priority score for addressing a coverage gap."""
        # Factors: coverage deficit, complexity, critical functions
        deficit_weight = (self.target_coverage - module.coverage_percentage) / 100
        complexity_weight = min(module.complexity_score / 10, 1.0)  # Normalize complexity
        critical_functions_weight = len(module.critical_functions) / 20  # Normalize function count

        priority = (deficit_weight * 0.5) + (complexity_weight * 0.3) + (critical_functions_weight * 0.2)
        return min(priority, 1.0)

    def _generate_recommendations(self, module_coverage: List[ModuleCoverage],
                                coverage_gaps: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations for improving coverage."""
        recommendations = []

        # Overall coverage recommendations
        overall_coverage = sum(m.coverage_percentage for m in module_coverage) / len(module_coverage) if module_coverage else 0

        if overall_coverage < self.target_coverage:
            recommendations.append(f"Overall coverage ({overall_coverage:.1f}%) is below target ({self.target_coverage:.1f}%)")

        # Module-specific recommendations
        for gap in coverage_gaps[:5]:  # Top 5 priority gaps
            module_name = gap['module']
            deficit = gap['coverage_deficit']
            missing_lines = gap['missing_lines_count']

            recommendations.append(
                f"📦 {module_name}: Add {missing_lines} lines of test coverage (deficit: {deficit:.1f}%)"
            )

            # Specific recommendations based on gap characteristics
            if gap['complexity_score'] > 5.0:
                recommendations.append(f"   Focus on testing complex logic in {module_name}")

            if gap['critical_functions_uncovered']:
                recommendations.append(f"   Ensure critical functions are tested: {', '.join(gap['critical_functions_uncovered'])}")

            if not gap['test_files']:
                recommendations.append(f"   Create test file for {module_name}")

        # General recommendations
        if len(coverage_gaps) > 10:
            recommendations.append("Consider implementing automated coverage monitoring")

        modules_without_tests = [m for m in module_coverage if not m.test_files_covering]
        if modules_without_tests:
            recommendations.append(f"Create test files for {len(modules_without_tests)} modules without tests")

        return recommendations

    def _generate_ai_analysis(self, module_coverage: List[ModuleCoverage], overall_coverage: float) -> Dict[str, Any]:
        """Generate AI-friendly analysis of coverage data."""
        analysis = {
            'coverage_health': 'excellent' if overall_coverage >= 98 else 'good' if overall_coverage >= 95 else 'needs_improvement',
            'test_completeness': overall_coverage / 100,
            'high_priority_modules': [],
            'testing_strategy_recommendations': [],
            'automation_opportunities': [],
            'quality_metrics': {},
            'risk_assessment': {}
        }

        # Identify high-priority modules
        for module in module_coverage:
            if module.coverage_percentage < 90 and module.complexity_score > 3:
                analysis['high_priority_modules'].append({
                    'module': module.module_name,
                    'coverage': module.coverage_percentage,
                    'complexity': module.complexity_score,
                    'risk_level': 'high'
                })

        # Testing strategy recommendations
        low_coverage_modules = [m for m in module_coverage if m.coverage_percentage < 80]
        if low_coverage_modules:
            analysis['testing_strategy_recommendations'].append("Implement unit testing for low-coverage modules")

        complex_modules = [m for m in module_coverage if m.complexity_score > 5]
        if complex_modules:
            analysis['testing_strategy_recommendations'].append("Focus on integration testing for complex modules")

        # Quality metrics
        analysis['quality_metrics'] = {
            'average_coverage': sum(m.coverage_percentage for m in module_coverage) / len(module_coverage) if module_coverage else 0,
            'coverage_variance': self._calculate_coverage_variance(module_coverage),
            'modules_above_95': sum(1 for m in module_coverage if m.coverage_percentage >= 95),
            'modules_below_80': sum(1 for m in module_coverage if m.coverage_percentage < 80),
            'total_critical_functions': sum(len(m.critical_functions) for m in module_coverage)
        }

        # Risk assessment
        analysis['risk_assessment'] = {
            'coverage_risk_score': max(0, (95 - overall_coverage) / 95),
            'complexity_risk_score': sum(m.complexity_score for m in module_coverage) / (len(module_coverage) * 10) if module_coverage else 0,
            'untested_critical_functions': sum(len(m.critical_functions) for m in module_coverage if m.coverage_percentage < 80)
        }

        return analysis

    def _calculate_coverage_variance(self, module_coverage: List[ModuleCoverage]) -> float:
        """Calculate variance in coverage across modules."""
        if not module_coverage:
            return 0.0

        coverages = [m.coverage_percentage for m in module_coverage]
        mean_coverage = sum(coverages) / len(coverages)
        variance = sum((c - mean_coverage) ** 2 for c in coverages) / len(coverages)
        return variance

    def generate_coverage_report(self, report: CoverageReport, output_dir: str = "coverage_reports") -> None:
        """Generate comprehensive coverage reports."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Generate JSON report (AI-friendly)
        json_report_path = output_path / "coverage_verification_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        # Generate summary report
        summary_path = output_path / "coverage_summary.txt"
        with open(summary_path, 'w') as f:
            self._write_coverage_summary(f, report)

        # Generate detailed module report
        detail_path = output_path / "module_coverage_details.json"
        with open(detail_path, 'w') as f:
            json.dump([m.to_dict() for m in report.module_coverage], f, indent=2)

        # Generate recommendations report
        recommendations_path = output_path / "coverage_recommendations.txt"
        with open(recommendations_path, 'w') as f:
            f.write("COVERAGE IMPROVEMENT RECOMMENDATIONS\n")
            f.write("=" * 50 + "\n\n")
            for i, rec in enumerate(report.recommendations, 1):
                f.write(f"{i}. {rec}\n")

        self.logger.info(f"Coverage reports generated in {output_dir}")

    def _write_coverage_summary(self, file, report: CoverageReport) -> None:
        """Write human-readable coverage summary."""
        file.write("=== TEST COVERAGE VERIFICATION SUMMARY ===\n\n")

        # Overall metrics
        file.write(f"🎯 Target Coverage: {report.target_coverage:.1f}%\n")
        file.write(f"📊 Overall Coverage: {report.overall_coverage:.1f}%\n")
        file.write(f"✅ Meets Threshold: {'Yes' if report.meets_threshold else 'No'}\n\n")

        # Module breakdown
        file.write(f"📦 Total Modules: {report.total_modules}\n")
        file.write(f"🟢 Above Threshold: {report.modules_above_threshold}\n")
        file.write(f"🔴 Below Threshold: {report.modules_below_threshold}\n\n")

        # Module details
        file.write("Module Coverage Details:\n")
        file.write("-" * 60 + "\n")
        for module in sorted(report.module_coverage, key=lambda x: x.coverage_percentage):
            status = "✅" if module.coverage_percentage >= report.target_coverage else "❌"
            file.write(f"{status} {module.module_name}: {module.coverage_percentage:.1f}% ({module.covered_lines}/{module.total_lines} lines)\n")

        # Coverage gaps
        if report.coverage_gaps:
            file.write(f"\n🔍 Coverage Gaps ({len(report.coverage_gaps)} modules):\n")
            for gap in report.coverage_gaps[:10]:  # Top 10
                file.write(f"   {gap['module']}: {gap['current_coverage']:.1f}% (deficit: {gap['coverage_deficit']:.1f}%)\n")

        # AI Analysis summary
        ai_analysis = report.ai_analysis
        file.write(f"\n🤖 AI Analysis:\n")
        file.write(f"   Health: {ai_analysis.get('coverage_health', 'unknown').title()}\n")
        file.write(f"   Quality Score: {ai_analysis.get('test_completeness', 0):.2f}\n")
        file.write(f"   High Priority Modules: {len(ai_analysis.get('high_priority_modules', []))}\n")


def main():
    """Main entry point for coverage verification."""
    verifier = CoverageVerifier(target_coverage=95.0)

    try:
        print("🔍 Starting comprehensive test coverage verification...")

        # Verify coverage
        report = verifier.verify_coverage()

        # Generate reports
        verifier.generate_coverage_report(report)

        # Print summary
        print(f"\n🏁 Coverage Verification Complete:")
        print(f"   Overall Coverage: {report.overall_coverage:.1f}%")
        print(f"   Target: {report.target_coverage:.1f}%")
        print(f"   Meets Threshold: {'✅ Yes' if report.meets_threshold else '❌ No'}")
        print(f"   Modules Above Threshold: {report.modules_above_threshold}/{report.total_modules}")

        if report.coverage_gaps:
            print(f"   Coverage Gaps: {len(report.coverage_gaps)} modules need attention")

        # Return appropriate exit code
        return 0 if report.meets_threshold else 1

    except Exception as e:
        print(f"❌ Coverage verification failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)