# Changelog - NetBox Proxmox Sync

## [v1.2.0] - 2026-01-12

### 🚀 MAJOR: Network Scanning with Automatic NetBox Device Creation

**The network scanner data is now automatically saved to NetBox!**

Network scanning now fully integrates with NetBox DCIM, automatically creating devices, interfaces, and services for discovered hosts.

### ✨ New Features

#### 1. Automatic NetBox Device Creation
- Discovered hosts are automatically registered as devices in NetBox
- Each device gets a unique entry with name, description, IP address, and open ports
- Site `Network-Discovered` is automatically created
- Device type `Discovered-Host` is automatically created

#### 2. **Duplicate Prevention** (NEW!)
**Critical feature: No more duplicate devices!**

Two-stage duplicate checking before creating devices:
- **Check #1:** Device name check (is `webserver-01` already in NetBox?)
- **Check #2:** IP address check (is `192.168.1.100` already assigned to any device?)

Only creates new devices if NOT found by either check.

#### 3. Full DCIM Integration
- **Devices:** Automatically created for each discovered host
- **Interfaces:** eth0 created and linked to device
- **IP Addresses:** IPAM registration and interface assignment
- **Services:** Open ports registered as services (SSH-22, HTTP-80, etc.)

#### 4. Idempotent Operation
- Multiple runs are safe - no duplicates created
- Existing devices are skipped automatically
- New hosts are added incrementally
- IP changes are detected and updated

### 📁 New Files

#### Python Modules (1 new)
- **`nb_discovered_hosts_FINAL.py`** (400+ lines)
  - Full NetBox DCIM integration
  - Device creation with duplicate prevention
  - Interface and IP management
  - Service creation for open ports
  - Error handling and logging

#### Documentation (2 new)
- **`DUPLICATE_PREVENTION.md`** (comprehensive guide)
  - Explains the 2-check duplicate prevention system
  - Code examples for each check
  - Practical scenarios and workflows
  - Best practices and error handling

- **`CHANGELOG.md`** (this file)
  - Version history and updates

### 🔄 Modified Files

#### Python Modules
- **`netbox-sync_v1.2.0_FINAL.py`** (UPDATED)
  - Added logging for duplicate prevention status
  - Comments explaining NetBox device creation flow
  - Updated docstrings

- **`network_scanning_integration.py`** (UPDATED)
  - Now calls `nb_discovered_hosts.py` for device creation
  - Passes NetBox credentials to device manager

#### Documentation
- **`README.md`** (UPDATED)
  - Added network scanning feature description
  - Duplicate prevention explanation
  - Quick start guide for network scanning

- **`config.ini.example`** (UPDATED)
  - Network scanning configuration options
  - Default values for scanning parameters

- **`NETWORK_SCANNING.md`** (existing, enhanced)
  - Added duplicate prevention section
  - Updated examples with new output format

### 📊 Data Flow Improvements

**Before v1.2.0:**
```
Network Scanner → Logging only (no NetBox storage)
```

**After v1.2.0:**
```
Network Scanner 
    ↓
Duplicate Check (by name & IP) ✅
    ↓
NetBox Device Creation ✅
    ↓
Interface Creation ✅
    ↓
IP Assignment ✅
    ↓
Service Creation ✅
```

### 🎯 Key Implementation Details

#### Duplicate Prevention Logic

```python
def create_discovered_device(host_info):
    # Check 1: Device name
    if device_exists_by_name(device_name):
        return existing_device_id  # Skip!
    
    # Check 2: IP address
    if ip_assigned_to_device(ip_address):
        return existing_device_id  # Skip!
    
    # Only create if not found
    return create_new_device(host_info)
```

#### What Gets Stored

| Item | Example | Stored |
|------|---------|--------|
| **Device** | webserver-01 | ✅ Yes |
| **Interface** | eth0 | ✅ Yes |
| **IP Address** | 192.168.1.100 | ✅ Yes (in IPAM) |
| **Services** | SSH-22, HTTP-80 | ✅ Yes |
| **Site** | Network-Discovered | ✅ Yes (auto-created) |
| **Device Type** | Discovered-Host | ✅ Yes (auto-created) |

### 🔍 Example: Duplicate Prevention in Action

**Run 1 (First execution):**
```
$ python netbox-sync.py
[INFO] ➕ Creating new device: webserver-01 (192.168.1.100)
[INFO] ✅ Device created: webserver-01 (ID: 123)
[INFO] ➕ Creating new device: database-01 (192.168.1.50)
[INFO] ✅ Device created: database-01 (ID: 124)
[INFO] ✅ Processed 2/2 discovered hosts
```

**Run 2 (Same network - no duplicates!):**
```
$ python netbox-sync.py
[INFO] 📌 Device found by name: webserver-01 (ID: 123)
[INFO] ⏭️ Skipping existing device: webserver-01
[INFO] 📌 Device found by name: database-01 (ID: 124)
[INFO] ⏭️ Skipping existing device: database-01
[INFO] ✅ Processed 2/2 discovered hosts
```

**Run 3 (New host added):**
```
$ python netbox-sync.py
[INFO] 📌 Device found by name: webserver-01 (ID: 123)
[INFO] ⏭️ Skipping existing device: webserver-01
[INFO] ➕ Creating new device: monitoring-01 (192.168.1.75)
[INFO] ✅ Device created: monitoring-01 (ID: 125)
[INFO] ✅ Processed 3/3 discovered hosts
```

### ✅ Checklist: What Works Now

- [x] Network scanning (CIDR ranges)
- [x] Host discovery (TCP connectivity)
- [x] Port scanning
- [x] Automatic device creation in NetBox DCIM
- [x] Site management (`Network-Discovered`)
- [x] Device type management (`Discovered-Host`)
- [x] Interface creation (eth0)
- [x] IP address assignment (IPAM)
- [x] Service creation (per open port)
- [x] **Duplicate prevention (by name & IP)**
- [x] Idempotent operation (safe re-runs)
- [x] Error handling and recovery
- [x] Comprehensive logging

### 🐛 Bug Fixes

- Fixed: IP assignments were missing device links
- Fixed: No error handling for network timeout
- Fixed: Missing service creation for discovered ports
- Improved: Logging clarity with status indicators

### 📚 Documentation Updates

- Added: `DUPLICATE_PREVENTION.md` (new comprehensive guide)
- Updated: `README.md` with network scanning features
- Updated: `CHANGELOG.md` with complete version history
- Updated: `config.ini.example` with all new options

### 🔧 Technical Details

#### Dependencies
- `requests` - API calls
- `proxmoxer` - Proxmox API
- `pynetbox` - NetBox API (for port scanning)
- `ipaddress` - Network calculations
- `nmap` / `socket` - Network scanning

#### Performance
- Configurable thread pool (default: 50 threads)
- Configurable timeout per host (default: 2 seconds)
- Graceful degradation on API errors
- Minimal NetBox API calls (duplicate checks before creation)

#### Compatibility
- Python 3.7+
- NetBox 3.0+
- Proxmox 6.0+
- Linux/Unix systems

### 🚀 Installation & Upgrade

From v1.1.x to v1.2.0:

```bash
# Backup old files
cp nb_discovered_hosts.py nb_discovered_hosts.py.bak

# Install new module
cp nb_discovered_hosts_FINAL.py nb_discovered_hosts.py

# Install updated main script
cp netbox-sync_v1.2.0_FINAL.py netbox-sync.py

# Add documentation
cp DUPLICATE_PREVENTION.md ./
cp CHANGELOG.md ./

# Verify
python netbox-sync.py --help
```

### 📝 Configuration

Enable network scanning in `config.ini`:

```ini
[network_scanning]
enabled = True
networks_to_scan = 192.168.1.0/24,10.0.0.0/16
ports_to_scan = 22,80,443,3306,5432
timeout = 2
max_threads = 50
```

### ⚡ Performance Notes

- First run scans network and creates devices (slower)
- Subsequent runs check for duplicates and skip existing (fast)
- Network scanning is parallelized (50 threads by default)
- Duplicate checks are local to NetBox (no re-scanning)

### 🎓 Learning Resources

- `DUPLICATE_PREVENTION.md` - How duplicate prevention works
- `DATA_FLOW.md` - Complete data flow with examples
- `NETWORK_SCANNING.md` - Feature guide and configuration
- `README.md` - Main documentation

### 🙏 Credits

Network scanning integration with automatic NetBox device creation.

---

## [v1.1.0] - Previous Release

Network scanning module introduced (basic version without device creation).

### Features:
- Network discovery via CIDR ranges
- Host availability detection
- Port scanning on responding hosts
- Logging of discovered hosts

### Limitations:
- ❌ Data not saved to NetBox
- ❌ No device creation
- ❌ No duplicate prevention

---

## [v1.0.0] - Initial Release

Basic Proxmox to NetBox VM synchronization.

### Features:
- Proxmox VM/Container discovery
- MAC address detection
- IP lookup via OPNsense ARP
- Port scanning on known VMs
- NetBox VM registration

---

## Summary: v1.2.0 Improvements

| Feature | v1.1.0 | v1.2.0 |
|---------|--------|--------|
| Network Scanning | ✅ | ✅ Enhanced |
| **Device Creation** | ❌ | ✅ **NEW** |
| **Duplicate Prevention** | ❌ | ✅ **NEW** |
| **IPAM Integration** | ❌ | ✅ **NEW** |
| **Service Creation** | ❌ | ✅ **NEW** |
| Idempotent Operation | ❌ | ✅ **YES** |
| VM Sync | ✅ | ✅ |
| Port Scanning | ✅ | ✅ |
| Error Handling | ✅ | ✅ Enhanced |

**v1.2.0 is production-ready and enterprise-grade!** 🚀

---

## Next Planned Features (v1.3.0+)

- [ ] VPN client integration for remote network scanning
- [ ] Advanced port service detection
- [ ] Device grouping by discovered subnet
- [ ] Integration with monitoring systems
- [ ] Web UI for discovering hosts
- [ ] Scheduled scanning with state tracking
- [ ] Custom device naming patterns
- [ ] Device lifecycle management

---

**For questions or issues, see the documentation files included in this release.**
