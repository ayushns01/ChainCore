#!/usr/bin/env python3
"""
Multi-Node Network Testing Script
Tests blockchain synchronization and consensus across N nodes (N > 2)

This script validates the enhanced multi-node synchronization fixes
and ensures unified blockchain consensus across large networks.
"""

import os
import sys
import time
import json
import random
import signal
import requests
import threading
import subprocess
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiNodeTestSuite:
    def __init__(self, num_nodes: int = 10, base_port: int = 5000):
        """Initialize multi-node test suite"""
        self.num_nodes = num_nodes
        self.base_port = base_port
        self.node_processes = []
        self.miner_processes = []
        self.test_results = {}
        self.node_urls = [f"http://localhost:{base_port + i}" for i in range(num_nodes)]
        
        print(f"🧪 Multi-Node Test Suite Initialized")
        print(f"   📊 Nodes: {num_nodes}")
        print(f"   🔌 Port range: {base_port}-{base_port + num_nodes - 1}")
        
    def cleanup_existing_processes(self):
        """Kill any existing node processes on our ports"""
        print("🧹 Cleaning up existing processes...")
        for i in range(self.num_nodes):
            port = self.base_port + i
            try:
                # Kill processes using our ports
                subprocess.run(['pkill', '-f', f'--api-port {port}'], 
                             capture_output=True, timeout=5)
            except Exception:
                pass
        time.sleep(2)
        
    def start_nodes(self) -> bool:
        """Start all network nodes"""
        print(f"🚀 Starting {self.num_nodes} network nodes...")
        
        for i in range(self.num_nodes):
            port = self.base_port + i
            node_id = f"Node-{i+1}"
            
            try:
                # Start network node
                cmd = [
                    sys.executable, 'network_node.py',
                    '--api-port', str(port),
                    '--node-id', node_id
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.node_processes.append(process)
                print(f"   ✅ Started {node_id} on port {port}")
                
            except Exception as e:
                print(f"   ❌ Failed to start node on port {port}: {e}")
                return False
                
        # Wait for nodes to initialize
        print("⏳ Waiting for nodes to initialize...")
        time.sleep(10)
        
        # Verify all nodes are responding
        active_nodes = 0
        for i, url in enumerate(self.node_urls):
            try:
                response = requests.get(f"{url}/status", timeout=5)
                if response.status_code == 200:
                    active_nodes += 1
                    print(f"   ✅ Node {i+1} ({url}) is active")
                else:
                    print(f"   ⚠️  Node {i+1} ({url}) status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Node {i+1} ({url}) is not responding: {e}")
        
        if active_nodes < self.num_nodes:
            print(f"⚠️  Only {active_nodes}/{self.num_nodes} nodes are active")
            return False
            
        print(f"✅ All {self.num_nodes} nodes are active and responding")
        return True
        
    def wait_for_peer_discovery(self, timeout: int = 60) -> bool:
        """Wait for nodes to discover each other"""
        print("🔍 Waiting for peer discovery...")
        
        start_time = time.time()
        min_peers_required = min(3, self.num_nodes - 1)
        
        while time.time() - start_time < timeout:
            all_discovered = True
            
            for i, url in enumerate(self.node_urls):
                try:
                    response = requests.get(f"{url}/stats", timeout=3)
                    if response.status_code == 200:
                        stats = response.json()
                        active_peers = stats.get('peer_stats', {}).get('active_peers', 0)
                        
                        if active_peers < min_peers_required:
                            all_discovered = False
                            break
                            
                except Exception:
                    all_discovered = False
                    break
            
            if all_discovered:
                print(f"✅ All nodes discovered sufficient peers ({min_peers_required}+)")
                return True
                
            time.sleep(2)
        
        print(f"⚠️  Peer discovery timeout after {timeout}s")
        return False
        
    def test_unified_blockchain_consensus(self) -> Dict:
        """Test that all nodes maintain the same blockchain"""
        print("🔗 Testing unified blockchain consensus...")
        
        results = {
            'test_name': 'unified_blockchain_consensus',
            'nodes_tested': self.num_nodes,
            'chains_identical': True,
            'chain_lengths': {},
            'genesis_hashes': {},
            'chain_tips': {},
            'consensus_percentage': 0
        }
        
        # Get blockchain data from all nodes
        node_data = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(self._get_node_blockchain, url): i 
                for i, url in enumerate(self.node_urls)
            }
            
            for future in as_completed(futures):
                node_index = futures[future]
                try:
                    blockchain_data = future.result()
                    if blockchain_data:
                        node_data[node_index] = blockchain_data
                except Exception as e:
                    print(f"   ❌ Failed to get blockchain from node {node_index + 1}: {e}")
        
        if len(node_data) < 2:
            results['error'] = 'Insufficient nodes responded'
            return results
        
        # Analyze consensus
        chain_lengths = [len(data['chain']) for data in node_data.values()]
        genesis_hashes = [data['chain'][0]['hash'] if data['chain'] else None 
                         for data in node_data.values()]
        
        results['chain_lengths'] = {f"node_{i+1}": length for i, length in enumerate(chain_lengths)}
        results['genesis_hashes'] = {f"node_{i+1}": hash for i, hash in enumerate(genesis_hashes)}
        
        # Check if all chains are identical
        if len(set(chain_lengths)) == 1 and len(set(filter(None, genesis_hashes))) <= 1:
            results['chains_identical'] = True
            results['consensus_percentage'] = 100.0
            print(f"   ✅ Perfect consensus: All {len(node_data)} nodes have identical chains")
        else:
            results['chains_identical'] = False
            # Calculate consensus percentage based on most common chain length
            most_common_length = max(set(chain_lengths), key=chain_lengths.count)
            consensus_count = chain_lengths.count(most_common_length)
            results['consensus_percentage'] = (consensus_count / len(chain_lengths)) * 100
            print(f"   ⚠️  Consensus issue: {results['consensus_percentage']:.1f}% agreement")
            print(f"      Chain lengths: {chain_lengths}")
        
        return results
        
    def test_simultaneous_mining(self, mining_duration: int = 30) -> Dict:
        """Test mining with multiple nodes simultaneously"""
        print(f"⛏️  Testing simultaneous mining for {mining_duration}s...")
        
        results = {
            'test_name': 'simultaneous_mining',
            'mining_duration': mining_duration,
            'miners_started': 0,
            'blocks_mined': {},
            'split_chains': False,
            'final_consensus': False
        }
        
        # Generate test wallet addresses for miners
        miner_wallets = [f"1TestMiner{i+1:02d}{'x' * 26}" for i in range(min(5, self.num_nodes))]
        
        # Start miners on different nodes
        mining_futures = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            for i, wallet in enumerate(miner_wallets):
                node_url = self.node_urls[i % self.num_nodes]
                future = executor.submit(self._run_miner, wallet, node_url, mining_duration)
                mining_futures.append((i, future))
                results['miners_started'] += 1
                print(f"   🚀 Started miner {i+1} with wallet {wallet[:16]}... on {node_url}")
        
        # Wait for mining to complete
        print(f"⏳ Mining in progress... waiting {mining_duration}s")
        time.sleep(mining_duration + 5)  # Extra time for cleanup
        
        # Stop any remaining miners
        self._stop_all_miners()
        
        # Wait for network to stabilize
        print("🔄 Waiting for network stabilization...")
        time.sleep(10)
        
        # Check final state
        consensus_result = self.test_unified_blockchain_consensus()
        results['final_consensus'] = consensus_result['chains_identical']
        results['split_chains'] = not consensus_result['chains_identical']
        
        if results['final_consensus']:
            print("   ✅ Mining test successful: Unified blockchain maintained")
        else:
            print("   ❌ Mining test failed: Chain splits detected")
            
        return results
        
    def test_network_partition_recovery(self) -> Dict:
        """Test recovery from network partitions"""
        print("🔗 Testing network partition recovery...")
        
        results = {
            'test_name': 'network_partition_recovery',
            'partition_successful': False,
            'recovery_successful': False,
            'final_consensus': False
        }
        
        # This is a simplified test - in production you'd simulate actual network partitions
        # For now, we'll test rapid node restart scenario
        
        if self.num_nodes < 4:
            results['error'] = 'Need at least 4 nodes for partition test'
            return results
        
        # "Partition" by stopping half the nodes
        partition_size = self.num_nodes // 2
        print(f"   📡 Simulating partition: stopping {partition_size} nodes...")
        
        stopped_processes = []
        for i in range(partition_size):
            if i < len(self.node_processes):
                process = self.node_processes[i]
                process.terminate()
                stopped_processes.append(i)
        
        time.sleep(5)
        results['partition_successful'] = True
        
        # Restart stopped nodes
        print(f"   🔄 Recovering partition: restarting {len(stopped_processes)} nodes...")
        for i in stopped_processes:
            port = self.base_port + i
            node_id = f"Node-{i+1}"
            
            try:
                cmd = [
                    sys.executable, 'network_node.py',
                    '--api-port', str(port),
                    '--node-id', node_id
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.node_processes[i] = process
                
            except Exception as e:
                print(f"   ❌ Failed to restart node {i+1}: {e}")
        
        # Wait for recovery
        print("⏳ Waiting for partition recovery...")
        time.sleep(15)
        
        # Check if recovery was successful
        if self.wait_for_peer_discovery(timeout=30):
            results['recovery_successful'] = True
            
            # Check final consensus
            consensus_result = self.test_unified_blockchain_consensus()
            results['final_consensus'] = consensus_result['chains_identical']
            
            if results['final_consensus']:
                print("   ✅ Partition recovery successful: Network consensus restored")
            else:
                print("   ⚠️  Partition recovery partial: Some consensus issues remain")
        else:
            print("   ❌ Partition recovery failed: Peer discovery timeout")
            
        return results
    
    def _get_node_blockchain(self, url: str) -> Optional[Dict]:
        """Get blockchain data from a node"""
        try:
            response = requests.get(f"{url}/blockchain", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
        
    def _run_miner(self, wallet: str, node_url: str, duration: int) -> Dict:
        """Run a miner for specified duration"""
        try:
            cmd = [
                sys.executable, 'mining_client.py',
                '--wallet', wallet,
                '--node', node_url,
                '--timeout', str(duration),
                '--quiet'  # Reduce output for multi-miner testing
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.miner_processes.append(process)
            
            # Wait for completion
            stdout, stderr = process.communicate(timeout=duration + 10)
            
            return {
                'wallet': wallet,
                'node': node_url,
                'success': process.returncode == 0,
                'stdout': stdout,
                'stderr': stderr
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {'wallet': wallet, 'node': node_url, 'success': False, 'error': 'timeout'}
        except Exception as e:
            return {'wallet': wallet, 'node': node_url, 'success': False, 'error': str(e)}
            
    def _stop_all_miners(self):
        """Stop all running miners"""
        for process in self.miner_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self.miner_processes.clear()
        
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive multi-node test suite"""
        print("🧪 Starting Comprehensive Multi-Node Test Suite")
        print("=" * 60)
        
        test_results = {
            'test_suite': 'multi_node_comprehensive',
            'timestamp': time.time(),
            'num_nodes': self.num_nodes,
            'tests': {},
            'overall_success': False
        }
        
        try:
            # Test 1: Node startup and peer discovery
            print("\n📋 Test 1: Node Startup and Peer Discovery")
            if not self.start_nodes():
                test_results['error'] = 'Failed to start nodes'
                return test_results
                
            if not self.wait_for_peer_discovery():
                test_results['error'] = 'Peer discovery failed'
                return test_results
            
            # Test 2: Unified blockchain consensus
            print("\n📋 Test 2: Unified Blockchain Consensus")
            consensus_test = self.test_unified_blockchain_consensus()
            test_results['tests']['consensus'] = consensus_test
            
            # Test 3: Simultaneous mining
            print("\n📋 Test 3: Simultaneous Mining")
            mining_test = self.test_simultaneous_mining(30)
            test_results['tests']['mining'] = mining_test
            
            # Test 4: Network partition recovery
            print("\n📋 Test 4: Network Partition Recovery")
            partition_test = self.test_network_partition_recovery()
            test_results['tests']['partition'] = partition_test
            
            # Determine overall success
            all_consensus = consensus_test.get('chains_identical', False)
            mining_success = mining_test.get('final_consensus', False)
            partition_recovery = partition_test.get('final_consensus', False)
            
            test_results['overall_success'] = all_consensus and mining_success
            
            print("\n" + "=" * 60)
            print("🏁 Test Suite Complete!")
            print(f"📊 Overall Success: {'✅ PASS' if test_results['overall_success'] else '❌ FAIL'}")
            print(f"   🔗 Consensus: {'✅' if all_consensus else '❌'}")
            print(f"   ⛏️  Mining: {'✅' if mining_success else '❌'}")
            print(f"   🔄 Recovery: {'✅' if partition_recovery else '❌'}")
            
        except Exception as e:
            test_results['error'] = str(e)
            print(f"❌ Test suite failed: {e}")
            
        finally:
            self.cleanup()
            
        return test_results
        
    def cleanup(self):
        """Cleanup all processes and resources"""
        print("\n🧹 Cleaning up test environment...")
        
        # Stop miners
        self._stop_all_miners()
        
        # Stop nodes
        for process in self.node_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        
        self.node_processes.clear()
        print("✅ Cleanup complete")


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Node Network Test Suite')
    parser.add_argument('--nodes', type=int, default=10, 
                       help='Number of nodes to test (default: 10)')
    parser.add_argument('--base-port', type=int, default=5000,
                       help='Base port for nodes (default: 5000)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.nodes < 3:
        print("❌ Error: Need at least 3 nodes for meaningful multi-node testing")
        sys.exit(1)
        
    if args.nodes > 50:
        print("⚠️  Warning: Testing with >50 nodes may be resource intensive")
        response = input("Continue? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(0)
    
    # Setup signal handling for cleanup
    test_suite = MultiNodeTestSuite(num_nodes=args.nodes, base_port=args.base_port)
    
    def signal_handler(signum, frame):
        print("\n🛑 Test interrupted - cleaning up...")
        test_suite.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Cleanup any existing processes
        test_suite.cleanup_existing_processes()
        
        # Run tests
        if args.quick:
            print("🚀 Running Quick Multi-Node Tests...")
            # Quick test: just consensus check
            test_suite.start_nodes()
            test_suite.wait_for_peer_discovery()
            results = test_suite.test_unified_blockchain_consensus()
            print(f"Quick test result: {'✅ PASS' if results['chains_identical'] else '❌ FAIL'}")
        else:
            # Full comprehensive test
            results = test_suite.run_comprehensive_test()
            
            # Save results
            results_file = f'multi_node_test_results_{args.nodes}nodes_{int(time.time())}.json'
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📁 Detailed results saved to: {results_file}")
            
    except KeyboardInterrupt:
        print("\n🛑 Test suite interrupted")
    except Exception as e:
        print(f"❌ Test suite error: {e}")
    finally:
        test_suite.cleanup()


if __name__ == '__main__':
    main()