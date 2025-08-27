# ChainCore Fixes Log

## Fix: Peer Discovery, Connection Issues, and Code Clarity

**Date:** 2025-08-26

### Issue

When starting multiple nodes, especially in a local test environment, nodes started after the initial group (e.g., a node on port 5003 started after 5000, 5001, 5002) would fail to show any connected peers. The new node would connect to a bootstrap node but would not register it as a valid peer, resulting in a peer count of zero.

The root cause was a significant architectural flaw in `network_node.py` where two different peer manager implementations were being used simultaneously:

1.  An older `ThreadSafePeerManager` from `src/concurrency/network_safe.py`.
2.  A newer, more feature-rich `EnhancedPeerManager` from `src/networking/peer_manager.py`.

The bootstrap logic was handled by the new manager, but all status reporting endpoints (`/status`, `/peers`, etc.) were reading their data from the old, unused manager. This created an inconsistent and non-functional state.

### Solution

The `network_node.py` file and associated modules were refactored to resolve the connectivity issues and improve code quality. The fix involved consolidating all peer-related operations to use a single, robust manager.

The following changes were made:

1.  **Consolidated Peer Manager:** Removed the old `ThreadSafePeerManager` and routed all calls to the newer manager, ensuring that the component handling bootstrapping is the same one that reports network status.
2.  **Compatibility & Correction:** Added a `get_active_peers()` method to the new manager for backward compatibility and corrected logic in all relevant functions (`_sync_with_network_before_mining`, `submit_block`, `/status`, `/peers`, etc.) to use the correct manager instance.
3.  **Cleanup:** Removed obsolete configuration and startup logic related to the old manager from the `start()` method.
4.  **Refactored Naming for Clarity:** Renamed the overly generic `EnhancedPeerManager` class to the more descriptive `PeerNetworkManager`. All instance variables were also renamed from `enhanced_peer_manager` to `peer_network_manager` to match. This code quality improvement makes the architecture clearer and fairer to maintain.
5.  **Disabled Obsolete Endpoint:** The manual `/sync_now` endpoint, which was tied to the old manager's logic, was disabled to prevent errors, as the new manager handles synchronization automatically.

---

## Fix: Node Status Endpoint (500 Internal Server Error)

**Date:** 2025-08-26

### Issue

After the peer manager refactoring, the `network_node.py` crashed with a `500 Internal Server Error` when its `/status` endpoint was accessed. This was because the `get_status` function was still attempting to access attributes and methods from the old `ThreadSafePeerManager` (e.g., `self.peer_manager._min_peers`, `self.peer_manager.get_main_node_status()`) which no longer exist.

### Solution

The entire `get_status` function in `network_node.py` was rewritten. It now exclusively uses the `PeerNetworkManager` to retrieve all status information. This involved:
*   Retrieving peer counts and status directly from `self.peer_network_manager.get_status()`.
*   Simplifying network health determination, as the new manager handles peer limits differently.
*   Removing references to the old `is_main_node` concept and related attributes.
*   Streamlining the JSON response to only include information correctly available from the `PeerNetworkManager`.

This ensures the node's status reporting is functional and consistent with the refactored peer management system.

---

## Fix: Missing `psutil` Dependency

**Date:** 2025-08-26

### Issue

The `psutil` library, an optional but recommended dependency for optimal multi-core mining performance, was not listed in `requirements.txt`.

### Solution

The `psutil` dependency was added to `requirements.txt` with a comment indicating its optional nature and purpose.