#!/usr/bin/env python3
"""
Test script for validating node startup and peer discovery fixes
Tests multiple node startup scenarios to ensure race conditions are resolved
"""

import subprocess
import time
import requests
import json
import sys
import signal
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

class NodeStartupTester:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.test_ports = [5010, 5011, 5012, 5013, 5014]  # Avoid common ports
        self.results = {}
        
    def cleanup(self):
        """Clean up all started processes"""
        print("🧹 Cleaning up test processes...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self.processes.clear()
        time.sleep(2)  # Allow ports to be released

    def start_node(self, node_id: str, port: int, delay: float = 0) -> subprocess.Popen:
        """Start a single node with optional delay"""
        if delay > 0:
            time.sleep(delay)
        
        print(f"🚀 Starting node {node_id} on port {port}")
        cmd = [
            "python", "network_node.py",
            "--node-id", node_id,
            "--api-port", str(port),
            "--quiet"  # Reduce output noise
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(process)
        return process

    def wait_for_node_ready(self, port: int, timeout: float = 30.0) -> bool:
        """Wait for a node to be ready and accepting connections"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{port}/status", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.5)
        return False

    def get_node_status(self, port: int) -> Optional[Dict]:
        """Get status information from a node"""
        try:
            response = requests.get(f"http://localhost:{port}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None

    def test_simultaneous_startup(self) -> bool:
        """Test multiple nodes starting simultaneously"""
        print("\n" + "="*60)
        print("🧪 TEST 1: Simultaneous Node Startup")
        print("="*60)
        
        # Start all nodes simultaneously using thread pool
        with ThreadPoolExecutor(max_workers=len(self.test_ports)) as executor:
            futures = [
                executor.submit(self.start_node, f"test_node_{i}", port)
                for i, port in enumerate(self.test_ports)
            ]
            
            # Wait for all to start
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Failed to start node: {e}")
        
        print(f"⏳ Waiting for {len(self.test_ports)} nodes to be ready...")
        
        # Wait for all nodes to be ready
        ready_nodes = []
        for port in self.test_ports:
            if self.wait_for_node_ready(port, timeout=45):  # Longer timeout for startup fixes
                ready_nodes.append(port)
                print(f"✅ Node on port {port} is ready")
            else:
                print(f"❌ Node on port {port} failed to start")
        
        # Check peer discovery results
        time.sleep(10)  # Allow time for peer discovery
        
        success = len(ready_nodes) == len(self.test_ports)
        print(f"\n📊 Startup Results: {len(ready_nodes)}/{len(self.test_ports)} nodes started successfully")
        
        # Analyze peer connections
        if ready_nodes:
            self.analyze_peer_connections(ready_nodes)
        
        return success

    def test_staggered_startup(self) -> bool:
        """Test nodes starting with delays (should work better)"""
        print("\n" + "="*60)
        print("🧪 TEST 2: Staggered Node Startup")
        print("="*60)
        
        # Clean up from previous test
        self.cleanup()
        
        # Start nodes with 3-second delays
        for i, port in enumerate(self.test_ports):
            delay = i * 3.0  # 0, 3, 6, 9, 12 second delays
            self.start_node(f"stagger_node_{i}", port, delay)
        
        print(f"⏳ Waiting for all nodes to start (with staggered timing)...")
        
        # Wait for all nodes to be ready
        ready_nodes = []
        max_wait_time = 60  # Longer wait for staggered startup
        
        for port in self.test_ports:
            if self.wait_for_node_ready(port, timeout=max_wait_time):
                ready_nodes.append(port)
                print(f"✅ Node on port {port} is ready")
            else:
                print(f"❌ Node on port {port} failed to start")
        
        # Allow time for peer discovery between all nodes
        time.sleep(15)
        
        success = len(ready_nodes) == len(self.test_ports)
        print(f"\n📊 Staggered Results: {len(ready_nodes)}/{len(self.test_ports)} nodes started successfully")
        
        if ready_nodes:
            self.analyze_peer_connections(ready_nodes)
        
        return success

    def analyze_peer_connections(self, ready_nodes: List[int]):
        """Analyze how well nodes discovered each other"""
        print("\n🔗 PEER CONNECTION ANALYSIS")
        print("-" * 40)
        
        total_possible_connections = len(ready_nodes) * (len(ready_nodes) - 1)
        actual_connections = 0
        
        for port in ready_nodes:
            status = self.get_node_status(port)
            if status:
                peer_count = status.get('peers', 0)
                actual_connections += peer_count
                print(f"📡 Node {port}: {peer_count} peers connected")
                
                # Get detailed blockchain info
                blockchain_length = status.get('blockchain_length', 0)
                node_id = status.get('node_id', 'unknown')
                uptime = status.get('uptime', 0)
                
                print(f"   🆔 ID: {node_id}")
                print(f"   📦 Blockchain: {blockchain_length} blocks")
                print(f"   ⏱️  Uptime: {uptime:.1f}s")
                print()
        
        if total_possible_connections > 0:
            connection_rate = (actual_connections / total_possible_connections) * 100
            print(f"📊 Connection Success Rate: {actual_connections}/{total_possible_connections} ({connection_rate:.1f}%)")
            
            if connection_rate >= 80:
                print("✅ Excellent peer discovery!")
            elif connection_rate >= 60:
                print("⚠️  Good peer discovery, some connections missing")
            else:
                print("❌ Poor peer discovery - significant connectivity issues")
        else:
            print("❌ No connections possible (insufficient nodes)")

    def test_port_conflict_resolution(self) -> bool:
        """Test automatic port conflict resolution"""
        print("\n" + "="*60)
        print("🧪 TEST 3: Port Conflict Resolution")
        print("="*60)
        
        self.cleanup()
        
        # Start multiple nodes on the same initial port (should auto-resolve)
        base_port = 5020
        conflicts_resolved = 0
        
        for i in range(3):
            try:
                process = self.start_node(f"conflict_node_{i}", base_port)
                time.sleep(2)  # Small delay between starts
                
                # Check if node found an alternative port
                for check_port in range(base_port, base_port + 10):
                    if self.wait_for_node_ready(check_port, timeout=10):
                        if check_port != base_port or i == 0:  # First node can use base port
                            conflicts_resolved += 1
                            print(f"✅ Node {i} resolved to port {check_port}")
                            break
                else:
                    print(f"❌ Node {i} failed to resolve port conflict")
                    
            except Exception as e:
                print(f"❌ Error starting conflict test node {i}: {e}")
        
        success = conflicts_resolved >= 2  # At least 2 nodes should resolve conflicts
        print(f"\n📊 Port Conflict Resolution: {conflicts_resolved}/3 nodes successfully resolved conflicts")
        
        return success

    def run_all_tests(self):
        """Run all startup tests"""
        print("🧪 ChainCore Node Startup Test Suite")
        print("Testing fixes for race conditions and peer discovery issues")
        print("="*70)
        
        test_results = {}
        
        try:
            # Test 1: Simultaneous startup (stress test)
            test_results['simultaneous'] = self.test_simultaneous_startup()
            
            # Test 2: Staggered startup (should work well)
            test_results['staggered'] = self.test_staggered_startup()
            
            # Test 3: Port conflict resolution
            test_results['port_conflicts'] = self.test_port_conflict_resolution()
            
        except KeyboardInterrupt:
            print("\n⏹️  Tests interrupted by user")
        except Exception as e:
            print(f"\n❌ Test suite error: {e}")
        finally:
            self.cleanup()
        
        # Summary
        print("\n" + "="*70)
        print("📋 TEST SUMMARY")
        print("="*70)
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.upper():20} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All startup fixes working correctly!")
            return True
        else:
            print("⚠️  Some issues remain - check logs above")
            return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode - just staggered startup
        tester = NodeStartupTester()
        try:
            success = tester.test_staggered_startup()
            sys.exit(0 if success else 1)
        finally:
            tester.cleanup()
    else:
        # Full test suite
        tester = NodeStartupTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Test interrupted - cleaning up...")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    main()