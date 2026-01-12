# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-12

### Added
- **Port Scanning Integration** - Auto-detect open ports on VMs
  - Socket-based TCP port scanning without external dependencies
  - Multi-threaded scanning (configurable up to 20 threads)
  - Automatic service creation in NetBox for detected ports
  - Configurable port ranges and individual ports
  - Smart port-to-service mapping (SSH, HTTP, MySQL, PostgreSQL, etc.)
  - 5-second timeout per port (configurable)
  - Full integration with VM synchronization workflow

- **New Python Modules**
  - `port_scanner.py` - Core port scanning logic with threading
  - `nb_services.py` - NetBox service and port management
  - `port_scanning_integration.py` - Integration with main sync script

- **Configuration**
  - New `[port_scanning]` section in config.ini
  - Options: enabled, ports_to_scan, timeout, max_threads

- **Documentation**
  - `PORT_SCANNING.md` - Comprehensive port scanning feature guide
  - Updated `README.md` with port scanning overview
  - Updated `INSTALL.md` with port scanning setup instructions

### Changed
- `netbox-sync.py` - Integrated port scanning into main sync workflow
- `config.ini.example` - Added port scanning configuration template

### Technical Details
- Uses `socket.socket` for TCP connection attempts
- ThreadPoolExecutor for parallel port scanning (default 20 threads)
- Supports port ranges (e.g., 3000-3100) and comma-separated lists
- Graceful error handling with fallback to skip scanning if modules missing
- Comprehensive logging of scan progress and results

## [1.0.0] - 2026-01-10

### Added
- Initial release
- Proxmox VM and container synchronization to NetBox
- MAC address detection from VM configurations
- IP address lookup via OPNsense ARP table
- Automatic device creation in NetBox cluster
- Network interface tracking
- VM status monitoring (running/offline)
- Disk, CPU, and memory information extraction

### Core Features
- **VM/Container Sync** - Automatically sync all Proxmox infrastructure
- **MAC Address Detection** - Extract MAC addresses from VM configs
- **IP Lookup** - Retrieve IPs via OPNsense ARP integration
- **Status Management** - Track VM operational status
- **Interface Tracking** - Monitor network interfaces
- **Dry-Run Mode** - Preview ethX to MAC to IP mappings

### Files
- `netbox-sync.py` - Main synchronization script
- `common.py` - Shared utilities
- `nb_vm.py` - VM management
- `nb_interfaces.py` - Network interface management
- `nb_ip.py` - IP address management
- `config.ini.example` - Configuration template
- `requirements.txt` - Python dependencies
- Documentation files (README.md, INSTALL.md, etc.)

### Configuration
- Proxmox API credentials (token-based authentication)
- NetBox API configuration
- OPNsense integration for ARP lookups
- Logging configuration

---

## Upgrade Guide

### From 1.0.0 to 1.1.0

1. Update your repository:
```bash
cd /opt/netbox-proxmox-sync
git pull origin main
```

2. Install new dependencies:
```bash
pip install pynetbox>=7.0.0
```

3. Update your config.ini with port scanning settings:
```ini
[port_scanning]
enabled = False  # Set to True to enable
ports_to_scan = 22,80,443,3306,5432,8080-8090
timeout = 5
max_threads = 20
```

4. Test the new features:
```bash
python netbox-sync.py --help
python netbox-sync.py  # Will run with port scanning if enabled
```

---

## Known Limitations

- Port scanning requires network connectivity to target VMs
- Service creation in NetBox is logged but not yet persisted to database
- Socket-based scanning has ~5 second timeout per port (configurable)
- Large port ranges (1-65535) will take significant time to scan

---

## Future Enhancements

- [ ] Actual NetBox service creation API integration
- [ ] Service update/delete capabilities
- [ ] Per-VM port scanning profiles
- [ ] Service status monitoring
- [ ] Performance metrics and statistics
- [ ] Web UI dashboard
- [ ] Database backup and restore
