#!/usr/bin/env python3
"""
Session Manager for ChainCore Network
Manages session folders for blockchain runs
"""

import os
import json
import time
from datetime import datetime
from typing import Optional

class SessionManager:
    """
    Manages session folders for blockchain network runs.
    Each blockchain startup gets a unique session folder.
    All nodes in the same run share the same session folder.
    """
    
    _instance = None
    _current_session_folder = None
    _session_start_time = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.base_sessions_dir = "sessions"
            self._initialized = True
    
    def get_current_session_folder(self) -> str:
        """
        Get the current session folder. Creates a new one if none exists
        or if this is a fresh blockchain run.
        """
        if self._current_session_folder is None:
            # Check if there's an existing active session we can join
            existing_session = self._find_active_session()
            if existing_session:
                self._current_session_folder = existing_session
                print(f"📁 Joined existing session: {os.path.basename(existing_session)}")
            else:
                self._create_new_session_folder()
        return self._current_session_folder
    
    def _find_active_session(self) -> Optional[str]:
        """
        Look for an existing active session with running nodes.
        Uses more flexible logic to find joinable sessions.
        """
        if not os.path.exists(self.base_sessions_dir):
            return None
        
        # Find recent sessions with active status or recent activity
        candidate_sessions = []
        current_time = time.time()
        
        for item in os.listdir(self.base_sessions_dir):
            session_path = os.path.join(self.base_sessions_dir, item)
            if os.path.isdir(session_path) and item.startswith('session_'):
                metadata_file = os.path.join(session_path, "session_metadata.json")
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    session_number = metadata.get('session_number', 0)
                    nodes = metadata.get('nodes', [])
                    
                    # Check if session is marked as active
                    if metadata.get('status') == 'active':
                        # Check for recent node activity (within 5 minutes)
                        has_recent_activity = False
                        for node in nodes:
                            last_seen = node.get('last_seen', 0)
                            if current_time - last_seen < 300:  # 5 minutes
                                has_recent_activity = True
                                break
                        
                        # If there's recent activity, check if nodes are actually running
                        if has_recent_activity:
                            candidate_sessions.append({
                                'path': session_path,
                                'number': session_number,
                                'metadata': metadata,
                                'recent_activity': has_recent_activity
                            })
                except:
                    continue
        
        # Sort by session number (most recent first) and try to join
        candidate_sessions.sort(key=lambda x: x['number'], reverse=True)
        
        for session in candidate_sessions:
            # Try to ping nodes in this session
            if self._has_active_nodes(session['metadata'].get('nodes', [])):
                return session['path']
        
        # If no active nodes found, but we have recent sessions, try the most recent one
        # This handles cases where nodes are starting up
        if candidate_sessions:
            most_recent = candidate_sessions[0]
            print(f"📁 No active nodes detected, but joining recent session: {os.path.basename(most_recent['path'])}")
            return most_recent['path']
        
        return None
    
    def _has_active_nodes(self, nodes: list) -> bool:
        """
        Check if any nodes in the list are currently running by attempting to connect.
        Uses more robust checking with longer timeouts and retry logic.
        """
        import requests
        
        active_found = False
        
        for node in nodes:
            api_port = node.get('api_port')
            if api_port:
                # Try multiple times with increasing timeouts
                for attempt, timeout in enumerate([1, 3, 5], 1):
                    try:
                        response = requests.get(
                            f"http://localhost:{api_port}/status", 
                            timeout=timeout
                        )
                        if response.status_code == 200:
                            # Update the last_seen timestamp for this node
                            node['last_seen'] = time.time()
                            print(f"✅ Found active node {node.get('node_id', 'unknown')} on port {api_port}")
                            active_found = True
                            break  # Success, move to next node
                    except requests.exceptions.RequestException:
                        if attempt == 3:  # Last attempt
                            print(f"❌ Node {node.get('node_id', 'unknown')} on port {api_port} not responding")
                        continue
        
        return active_found
    
    def _create_new_session_folder(self):
        """Create a new session folder with sequential numbering"""
        timestamp = datetime.now()
        
        # Find the next available session number
        session_number = self._get_next_session_number()
        session_name = f"session_{session_number}"
        
        self._current_session_folder = os.path.join(self.base_sessions_dir, session_name)
        self._session_start_time = timestamp
        
        # Create the session directory
        os.makedirs(self._current_session_folder, exist_ok=True)
        
        # Create session metadata file
        metadata = {
            "session_name": session_name,
            "session_number": session_number,
            "session_start_time": timestamp.isoformat(),
            "blockchain_start_timestamp": time.time(),
            "nodes": [],
            "status": "active"
        }
        
        metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📁 New session created: {session_name}")
        return self._current_session_folder
    
    def _get_next_session_number(self) -> int:
        """Find the next available session number by checking existing folders"""
        if not os.path.exists(self.base_sessions_dir):
            os.makedirs(self.base_sessions_dir, exist_ok=True)
            return 1
        
        existing_numbers = []
        for item in os.listdir(self.base_sessions_dir):
            session_path = os.path.join(self.base_sessions_dir, item)
            if os.path.isdir(session_path) and item.startswith('session_'):
                try:
                    # Extract number from session_X format
                    number_str = item.replace('session_', '')
                    # Handle both numeric (session_1) and timestamp (session_20250107_143022) formats
                    if number_str.isdigit():
                        existing_numbers.append(int(number_str))
                    elif '_' in number_str:
                        # This is a timestamp format from previous implementation
                        # We'll convert it to a high number to avoid conflicts
                        existing_numbers.append(999 + len(existing_numbers))
                except:
                    continue
        
        # Return next sequential number
        return max(existing_numbers, default=0) + 1
    
    def register_node(self, node_id: str, api_port: int, p2p_port: int):
        """Register a node in the current session"""
        session_folder = self.get_current_session_folder()
        metadata_file = os.path.join(session_folder, "session_metadata.json")
        
        # Read existing metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except:
            metadata = {"nodes": []}
        
        # Add node info with heartbeat timestamp
        node_info = {
            "node_id": node_id,
            "api_port": api_port,
            "p2p_port": p2p_port,
            "registration_time": datetime.now().isoformat(),
            "last_seen": time.time()
        }
        
        # Check if node already registered and update it, otherwise add new
        existing_nodes = {n['node_id']: n for n in metadata.get('nodes', [])}
        if node_id in existing_nodes:
            # Update existing node's last_seen timestamp
            for node in metadata['nodes']:
                if node['node_id'] == node_id:
                    node['last_seen'] = time.time()
                    node['registration_time'] = datetime.now().isoformat()  # Update registration time too
                    break
        else:
            metadata['nodes'].append(node_info)
        
        # Ensure session is marked as active when nodes register
        metadata['status'] = 'active'
        
        # Update metadata file
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📝 Registered {node_id} in session {os.path.basename(session_folder)}")
        
        # Check if we can consolidate fragmented sessions
        self._consolidate_sessions_if_needed()
    
    def update_node_heartbeat(self, node_id: str):
        """Update the heartbeat timestamp for a node to show it's still active"""
        if not self._current_session_folder:
            return
        
        metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Update the last_seen timestamp for this node
            for node in metadata.get('nodes', []):
                if node.get('node_id') == node_id:
                    node['last_seen'] = time.time()
                    break
            
            # Write back the updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error updating heartbeat for {node_id}: {e}")
    
    def get_session_info(self) -> dict:
        """Get information about the current session"""
        if self._current_session_folder is None:
            return {"status": "no_active_session"}
        
        metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            return {
                "status": "active",
                "session_folder": os.path.basename(self._current_session_folder),
                "full_path": self._current_session_folder,
                **metadata
            }
        except:
            return {"status": "error", "message": "Could not read session metadata"}
    
    def list_all_sessions(self) -> list:
        """List all session folders"""
        sessions = []
        if os.path.exists(self.base_sessions_dir):
            for item in os.listdir(self.base_sessions_dir):
                session_path = os.path.join(self.base_sessions_dir, item)
                if os.path.isdir(session_path):
                    metadata_file = os.path.join(session_path, "session_metadata.json")
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        sessions.append({
                            "session_name": item,
                            "path": session_path,
                            "metadata": metadata
                        })
                    except:
                        # Legacy session or missing metadata
                        sessions.append({
                            "session_name": item,
                            "path": session_path,
                            "metadata": {"status": "legacy"}
                        })
        return sessions
    
    def force_new_session(self):
        """Force creation of a new session folder with next sequential number"""
        # Mark current session as completed if it exists
        if self._current_session_folder and os.path.exists(self._current_session_folder):
            metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                metadata['status'] = 'completed'
                metadata['end_time'] = datetime.now().isoformat()
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except:
                pass
        
        self._current_session_folder = None
        return self._create_new_session_folder()
    
    def _consolidate_sessions_if_needed(self):
        """Check if multiple recent sessions should be consolidated"""
        try:
            if not os.path.exists(self.base_sessions_dir):
                return
            
            current_time = time.time()
            recent_sessions = []
            
            # Find sessions with recent activity (within 10 minutes)
            for item in os.listdir(self.base_sessions_dir):
                session_path = os.path.join(self.base_sessions_dir, item)
                if os.path.isdir(session_path) and item.startswith('session_'):
                    metadata_file = os.path.join(session_path, "session_metadata.json")
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        if metadata.get('status') == 'active':
                            nodes = metadata.get('nodes', [])
                            for node in nodes:
                                last_seen = node.get('last_seen', 0)
                                if current_time - last_seen < 600:  # 10 minutes
                                    recent_sessions.append({
                                        'path': session_path,
                                        'number': metadata.get('session_number', 0),
                                        'metadata': metadata
                                    })
                                    break
                    except:
                        continue
            
            # If we have multiple recent active sessions, suggest consolidation
            if len(recent_sessions) > 1:
                session_numbers = [s['number'] for s in recent_sessions]
                print(f"💡 Detected fragmented sessions: {session_numbers}. Consider restarting all nodes to use a single session.")
        except Exception as e:
            print(f"⚠️ Error during session consolidation check: {e}")
    
    def update_mining_stats(self):
        """Update session metadata with mining statistics from all node session files"""
        if not self._current_session_folder:
            return
        
        metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
        try:
            # Read current metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Collect mining statistics from all node session files in this session
            mining_stats = {}
            total_blocks_mined = 0
            
            # Scan all session files in this session folder
            if os.path.exists(self._current_session_folder):
                for filename in os.listdir(self._current_session_folder):
                    if filename.startswith('session_') and filename.endswith('.json') and filename != 'session_metadata.json':
                        filepath = os.path.join(self._current_session_folder, filename)
                        try:
                            with open(filepath, 'r') as f:
                                node_data = json.load(f)
                            
                            node_id = node_data.get('node_id', 'unknown')
                            blocks_mined = node_data.get('blocks_mined', [])
                            block_count = len(blocks_mined)
                            
                            mining_stats[node_id] = {
                                'blocks_mined_count': block_count,
                                'session_file': filename,
                                'start_time': node_data.get('start_time'),
                                'latest_blocks': [
                                    {
                                        'block_index': block.get('block_index'),
                                        'block_hash': block.get('block_hash', '')[:16] + '...',
                                        'timestamp': block.get('timestamp')
                                    } for block in blocks_mined[-5:]  # Last 5 blocks
                                ]
                            }
                            total_blocks_mined += block_count
                            
                        except Exception as e:
                            print(f"⚠️ Error reading session file {filename}: {e}")
                            continue
            
            # Update metadata with mining statistics
            metadata['mining_statistics'] = {
                'total_blocks_mined': total_blocks_mined,
                'blocks_per_core': mining_stats,
                'last_updated': datetime.now().isoformat()
            }
            
            # Write updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
        except Exception as e:
            print(f"⚠️ Error updating mining stats: {e}")
    
    def close_current_session(self):
        """Mark the current session as completed"""
        if self._current_session_folder and os.path.exists(self._current_session_folder):
            # Update final mining statistics before closing
            self.update_mining_stats()
            
            metadata_file = os.path.join(self._current_session_folder, "session_metadata.json")
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                metadata['status'] = 'completed'
                metadata['end_time'] = datetime.now().isoformat()
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"✅ Closed session: {os.path.basename(self._current_session_folder)}")
            except Exception as e:
                print(f"⚠️ Error closing session: {e}")
    
    def check_and_cleanup_inactive_sessions(self):
        """
        Check all active sessions and mark them as completed if no nodes are running.
        This is called periodically to clean up sessions when all nodes stop.
        """
        if not os.path.exists(self.base_sessions_dir):
            return
        
        for item in os.listdir(self.base_sessions_dir):
            session_path = os.path.join(self.base_sessions_dir, item)
            if os.path.isdir(session_path) and item.startswith('session_'):
                metadata_file = os.path.join(session_path, "session_metadata.json")
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Only check sessions that are marked as active
                    if metadata.get('status') == 'active':
                        nodes = metadata.get('nodes', [])
                        if not self._has_active_nodes(nodes):
                            # No nodes are active, mark session as completed
                            metadata['status'] = 'completed'
                            metadata['end_time'] = datetime.now().isoformat()
                            with open(metadata_file, 'w') as f:
                                json.dump(metadata, f, indent=2)
                            print(f"🔒 Auto-closed inactive session: {item}")
                except Exception as e:
                    print(f"⚠️ Error checking session {item}: {e}")
    
    def get_active_nodes_count(self) -> int:
        """Get the count of currently active nodes across all sessions"""
        if not os.path.exists(self.base_sessions_dir):
            return 0
        
        total_active = 0
        for item in os.listdir(self.base_sessions_dir):
            session_path = os.path.join(self.base_sessions_dir, item)
            if os.path.isdir(session_path) and item.startswith('session_'):
                metadata_file = os.path.join(session_path, "session_metadata.json")
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if metadata.get('status') == 'active':
                        nodes = metadata.get('nodes', [])
                        for node in nodes:
                            api_port = node.get('api_port')
                            if api_port:
                                try:
                                    import requests
                                    response = requests.get(
                                        f"http://localhost:{api_port}/status", 
                                        timeout=1
                                    )
                                    if response.status_code == 200:
                                        total_active += 1
                                except:
                                    continue
                except:
                    continue
        
        return total_active
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)"""
        cls._instance = None
        cls._current_session_folder = None
        cls._session_start_time = None

# Global instance
session_manager = SessionManager()