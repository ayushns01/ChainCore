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
        Only creates new session if NO nodes are currently active.
        """
        if not os.path.exists(self.base_sessions_dir):
            return None
        
        # Find the most recent active session
        active_sessions = []
        for item in os.listdir(self.base_sessions_dir):
            session_path = os.path.join(self.base_sessions_dir, item)
            if os.path.isdir(session_path) and item.startswith('session_'):
                metadata_file = os.path.join(session_path, "session_metadata.json")
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if session is marked as active
                    if metadata.get('status') == 'active':
                        # Check if any nodes in this session are actually running
                        if self._has_active_nodes(metadata.get('nodes', [])):
                            active_sessions.append({
                                'path': session_path,
                                'number': metadata.get('session_number', 0),
                                'metadata': metadata
                            })
                except:
                    continue
        
        # Return the highest numbered active session with running nodes
        if active_sessions:
            latest_session = max(active_sessions, key=lambda x: x['number'])
            return latest_session['path']
        
        return None
    
    def _has_active_nodes(self, nodes: list) -> bool:
        """
        Check if any nodes in the list are currently running by attempting to connect.
        """
        import requests
        
        for node in nodes:
            api_port = node.get('api_port')
            if api_port:
                try:
                    # Quick health check to see if node is responsive
                    response = requests.get(
                        f"http://localhost:{api_port}/status", 
                        timeout=2
                    )
                    if response.status_code == 200:
                        # Update the last_seen timestamp for this node
                        node['last_seen'] = time.time()
                        return True  # At least one node is active
                except:
                    continue
        
        return False  # No nodes are responsive
    
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
    
    def close_current_session(self):
        """Mark the current session as completed"""
        if self._current_session_folder and os.path.exists(self._current_session_folder):
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