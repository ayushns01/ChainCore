# ChainCore Bug Fixes Summary

This document summarizes the bugs identified and fixed in the ChainCore project.

---

### 1. Separate Chains & Faulty Fork Resolution

*   **Problem:** Nodes were not agreeing on a single blockchain. Each node would create its own separate chain, leading to network fragmentation.
*   **Fix:** The root cause was a faulty, local-only fork resolution mechanism. This was replaced with a robust, network-aware consensus logic (`BlockchainSync`) that correctly uses the "heaviest chain" rule. This ensures all nodes will converge on a single, unified ledger.

---

### 2. Isolated Node Mining

*   **Problem:** A node with zero connections to other peers was still able to mine blocks. This created invalid chains and wasted CPU resources.
*   **Fix:** A guard was added to the mining process. Nodes now check if they have active peer connections before starting to mine. If a node is isolated, it will pause mining until it successfully reconnects to the network.

---

### 3. Bootstrap Connection Failures

*   **Problem:** When starting a new node and pointing it to a bootstrap node, the connection would sometimes fail, leaving the new node with 0 peers. This was due to a race condition where the new node tried to connect before the bootstrap node was fully ready.
*   **Fix:** A retry mechanism was added to the bootstrap process. A new node will now attempt to connect to its bootstrap peer multiple times before failing, which resolves the timing issue.

---

### 4. "Unknown Miner" in Blockchain Monitor

*   **Problem:** The blockchain monitor displayed "Mined by: Unknown Node" and "Address: unknown" for all new blocks.
*   **Fix:** The miner's metadata (address and node ID) was being lost when a node processed a block. The logic for creating a block from received data was corrected to ensure all metadata is properly preserved and stored on the blockchain.

---

### 5. Database Monitor Failures

*   **Problem:** The `database_monitor.py` script was constantly showing `Error getting blockchain length: 0` and was unable to display the correct chain length.
*   **Fix:** The bug was in the database access code (`block_dao.py`). A line that was trying to read a database query result by a numeric position (`result[0]`) was corrected to read it by its proper column name (`result['length']`).

---

### 6. Incorrect Command-Line Documentation

*   **Problem:** The `TERMINAL_COMMANDS.md` file contained incorrect examples for a command-line argument that did not exist (`--add-peer`).
*   **Fix:** The documentation was edited to remove all incorrect examples and text. It now accurately shows that `--bootstrap-nodes` is the correct argument for connecting a new node to the network.
