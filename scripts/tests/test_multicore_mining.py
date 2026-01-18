#!/usr/bin/env python3
"""
Multi-Core Mining Performance Test Script
Tests and benchmarks the multi-core mining implementation
"""

import os
import sys
import time
import json
import subprocess
import threading
from typing import Dict, List, Optional
import multiprocessing

class MultiCoreMiningTester:
    def __init__(self):
        self.test_results = {}
        self.node_process = None
        self.node_url = "http://localhost:5000"
        self.test_wallet = "1TestMultiCore1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZtest123"
        
    def start_test_node(self) -> bool:
        """Start a test node for mining"""
        print("🚀 Starting test network node...")
        
        try:
            # Start network node
            cmd = [
                sys.executable, 'network_node.py',
                '--api-port', '5000',
                '--node-id', 'MultiCoreTestNode'
            ]
            
            self.node_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for node to initialize
            print("⏳ Waiting for node initialization...")
            time.sleep(8)
            
            # Verify node is running
            try:
                import requests
                response = requests.get(f"{self.node_url}/status", timeout=5)
                if response.status_code == 200:
                    print("✅ Test node is running and responsive")
                    return True
                else:
                    print(f"❌ Node returned status {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Failed to connect to test node: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start test node: {e}")
            return False
    
    def stop_test_node(self):
        """Stop the test node"""
        if self.node_process:
            print("🛑 Stopping test node...")
            self.node_process.terminate()
            try:
                self.node_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.node_process.kill()
            self.node_process = None
    
    def test_cpu_detection(self) -> Dict:
        """Test CPU core detection"""
        print("\n💻 Testing CPU Core Detection...")
        
        result = {}
        try:
            # Test show-cores functionality
            cmd = [
                sys.executable, 'mining_client.py',
                '--wallet', self.test_wallet,
                '--show-cores'
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                output = process.stdout
                print("✅ CPU detection successful:")
                print(output)
                
                # Parse output for cores
                lines = output.split('\n')
                for line in lines:
                    if 'Detected CPU cores:' in line:
                        cores = int(line.split(':')[1].strip())
                        result['detected_cores'] = cores
                        break
                
                result['success'] = True
            else:
                print(f"❌ CPU detection failed: {process.stderr}")
                result['success'] = False
                result['error'] = process.stderr
                
        except Exception as e:
            print(f"❌ CPU detection test error: {e}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def benchmark_single_vs_multicore(self, duration: int = 30) -> Dict:
        """Benchmark single-core vs multi-core mining performance"""
        print(f"\n⚡ Benchmarking Single-Core vs Multi-Core ({duration}s each)...")
        
        results = {
            'single_core': {},
            'multi_core': {},
            'performance_improvement': 0
        }
        
        # Test single-core mining
        print("📊 Testing single-core mining...")
        single_result = self._run_mining_benchmark(
            single_core=True, 
            duration=duration,
            test_name="single-core"
        )
        results['single_core'] = single_result
        
        time.sleep(2)  # Brief pause between tests
        
        # Test multi-core mining
        print("📊 Testing multi-core mining...")
        multi_result = self._run_mining_benchmark(
            single_core=False,
            duration=duration,
            test_name="multi-core"
        )
        results['multi_core'] = multi_result
        
        # Calculate performance improvement
        if (single_result.get('success') and multi_result.get('success') and 
            single_result.get('hash_rate', 0) > 0):
            
            improvement = (multi_result.get('hash_rate', 0) / single_result.get('hash_rate', 1)) * 100
            results['performance_improvement'] = improvement
            
            print(f"\n📈 Performance Results:")
            print(f"   Single-core: {single_result.get('hash_rate', 0):.1f} H/s")
            print(f"   Multi-core:  {multi_result.get('hash_rate', 0):.1f} H/s")
            print(f"   Improvement: {improvement:.1f}%")
        
        return results
    
    def _run_mining_benchmark(self, single_core: bool, duration: int, test_name: str) -> Dict:
        """Run a mining benchmark test"""
        result = {
            'test_name': test_name,
            'duration': duration,
            'single_core': single_core,
            'success': False,
            'hash_rate': 0,
            'total_hashes': 0
        }
        
        try:
            # Build mining command
            cmd = [
                sys.executable, 'mining_client.py',
                '--wallet', self.test_wallet,
                '--node', self.node_url,
                '--timeout', str(duration),
                '--quiet'
            ]
            
            if single_core:
                cmd.extend(['--single-core'])
            
            # Run mining process
            start_time = time.time()
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 10  # Extra time for cleanup
            )
            actual_duration = time.time() - start_time
            
            # Parse output for hash rate
            output = process.stdout + process.stderr
            hash_rate = self._extract_hash_rate(output)
            total_hashes = hash_rate * actual_duration if hash_rate > 0 else 0
            
            result.update({
                'success': True,
                'hash_rate': hash_rate,
                'total_hashes': int(total_hashes),
                'actual_duration': actual_duration,
                'return_code': process.returncode
            })
            
            print(f"   ✅ {test_name}: {hash_rate:.1f} H/s")
            
        except subprocess.TimeoutExpired:
            result['error'] = 'Mining process timeout'
            print(f"   ⏰ {test_name}: Timeout")
        except Exception as e:
            result['error'] = str(e)
            print(f"   ❌ {test_name}: Error - {e}")
        
        return result
    
    def _extract_hash_rate(self, output: str) -> float:
        """Extract hash rate from mining output"""
        lines = output.split('\n')
        
        # Look for hash rate in various formats
        for line in lines:
            if 'H/s' in line:
                try:
                    # Extract number before H/s
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'H/s' in part:
                            # Try previous part as number
                            if i > 0:
                                hash_rate_str = parts[i-1].replace(',', '')
                                return float(hash_rate_str)
                except ValueError:
                    continue
        
        return 0.0
    
    def test_worker_configurations(self) -> Dict:
        """Test different worker configurations"""
        print("\n⚙️  Testing Different Worker Configurations...")
        
        cpu_cores = multiprocessing.cpu_count()
        configurations = [1, 2, 4, cpu_cores, cpu_cores * 2]
        configurations = [c for c in configurations if c <= cpu_cores * 2]  # Reasonable limit
        
        results = {}
        
        for workers in configurations:
            print(f"📊 Testing {workers} workers...")
            
            try:
                cmd = [
                    sys.executable, 'mining_client.py',
                    '--wallet', self.test_wallet,
                    '--node', self.node_url,
                    '--workers', str(workers),
                    '--timeout', '15',  # Shorter test for multiple configs
                    '--quiet'
                ]
                
                start_time = time.time()
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                duration = time.time() - start_time
                
                output = process.stdout + process.stderr
                hash_rate = self._extract_hash_rate(output)
                
                results[workers] = {
                    'workers': workers,
                    'hash_rate': hash_rate,
                    'duration': duration,
                    'success': hash_rate > 0
                }
                
                print(f"   ✅ {workers} workers: {hash_rate:.1f} H/s")
                
            except Exception as e:
                results[workers] = {
                    'workers': workers,
                    'error': str(e),
                    'success': False
                }
                print(f"   ❌ {workers} workers: Error - {e}")
            
            time.sleep(1)  # Brief pause between tests
        
        # Find optimal configuration
        best_config = None
        best_hash_rate = 0
        for config, result in results.items():
            if result.get('success') and result.get('hash_rate', 0) > best_hash_rate:
                best_hash_rate = result['hash_rate']
                best_config = config
        
        if best_config:
            print(f"\n🏆 Optimal configuration: {best_config} workers ({best_hash_rate:.1f} H/s)")
        
        return results
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive multi-core mining tests"""
        print("🧪 Multi-Core Mining Comprehensive Test Suite")
        print("=" * 60)
        
        test_results = {
            'timestamp': time.time(),
            'tests': {},
            'summary': {}
        }
        
        try:
            # Start test environment
            if not self.start_test_node():
                test_results['error'] = 'Failed to start test node'
                return test_results
            
            # Test 1: CPU Detection
            cpu_test = self.test_cpu_detection()
            test_results['tests']['cpu_detection'] = cpu_test
            
            if not cpu_test.get('success'):
                print("❌ CPU detection failed, skipping other tests")
                return test_results
            
            # Test 2: Single vs Multi-core benchmark
            benchmark_test = self.benchmark_single_vs_multicore(30)
            test_results['tests']['performance_benchmark'] = benchmark_test
            
            # Test 3: Worker configurations
            worker_test = self.test_worker_configurations()
            test_results['tests']['worker_configurations'] = worker_test
            
            # Generate summary
            summary = self._generate_test_summary(test_results['tests'])
            test_results['summary'] = summary
            
            print("\n" + "=" * 60)
            print("🏁 Multi-Core Mining Test Complete!")
            print(f"📊 Summary:")
            print(f"   CPU Cores: {summary.get('detected_cores', 'Unknown')}")
            print(f"   Performance Gain: {summary.get('performance_improvement', 0):.1f}%")
            print(f"   Optimal Workers: {summary.get('optimal_workers', 'Unknown')}")
            print(f"   All Tests: {'✅ PASS' if summary.get('all_tests_passed') else '❌ FAIL'}")
            
        except Exception as e:
            print(f"❌ Test suite error: {e}")
            test_results['error'] = str(e)
        
        finally:
            self.stop_test_node()
        
        return test_results
    
    def _generate_test_summary(self, tests: Dict) -> Dict:
        """Generate summary of test results"""
        summary = {}
        
        # CPU detection
        cpu_test = tests.get('cpu_detection', {})
        summary['detected_cores'] = cpu_test.get('detected_cores', 0)
        
        # Performance improvement
        benchmark = tests.get('performance_benchmark', {})
        summary['performance_improvement'] = benchmark.get('performance_improvement', 0)
        
        # Optimal workers
        worker_configs = tests.get('worker_configurations', {})
        best_workers = None
        best_rate = 0
        for workers, result in worker_configs.items():
            if result.get('success') and result.get('hash_rate', 0) > best_rate:
                best_rate = result['hash_rate']
                best_workers = workers
        summary['optimal_workers'] = best_workers
        summary['optimal_hash_rate'] = best_rate
        
        # Overall success
        summary['all_tests_passed'] = (
            cpu_test.get('success', False) and
            benchmark.get('multi_core', {}).get('success', False) and
            best_workers is not None
        )
        
        return summary


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Core Mining Test Suite')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only (shorter duration)')
    parser.add_argument('--cpu-only', action='store_true',
                       help='Test CPU detection only')
    parser.add_argument('--benchmark-only', action='store_true',
                       help='Run performance benchmark only')
    
    args = parser.parse_args()
    
    tester = MultiCoreMiningTester()
    
    try:
        if args.cpu_only:
            # Just test CPU detection
            result = tester.test_cpu_detection()
            print(f"CPU test result: {'✅ PASS' if result.get('success') else '❌ FAIL'}")
            
        elif args.benchmark_only:
            # Run benchmark only
            if tester.start_test_node():
                result = tester.benchmark_single_vs_multicore(15 if args.quick else 30)
                improvement = result.get('performance_improvement', 0)
                print(f"Performance improvement: {improvement:.1f}%")
                tester.stop_test_node()
            else:
                print("❌ Failed to start test node")
                
        else:
            # Full test suite
            duration = 15 if args.quick else 30
            results = tester.run_comprehensive_test()
            
            # Save results
            results_file = f'multicore_mining_test_results_{int(time.time())}.json'
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📁 Detailed results saved to: {results_file}")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        tester.stop_test_node()
    except Exception as e:
        print(f"❌ Test error: {e}")
        tester.stop_test_node()


if __name__ == '__main__':
    main()