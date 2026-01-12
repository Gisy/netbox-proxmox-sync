# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-12

### Added
- **Network Scanning** - Discover and scan entire networks/subnets
  - CIDR notation support (192.168.1.0/24, 10.0.0.0/8)
  - IP range support (172.16.0.1-172.16.0.254)
  - Active host discovery (TCP health checks on ports 443/80)
  - Multi-threaded host discovery (configurable up to 50 threads)
  - Port scanning on discovered hosts
  - Automatic hostname resolution
  - Network sampling for large subnets (/8 or larger)
  - Graceful handling of large network ranges

- **New Python Modules**
  - `network_scanner.py` - Core network scanning logic with ipaddress module
  - `network_scanning_integration.py` - Integration with main sync script

- **Configuration**
  - New `[network_scanning]` section in config.ini
  - Options: enabled, networks_to_scan, ports_to_scan, timeout, max_threads
  - Support for multiple networks (comma-separated)

- **Documentation**
  - `NETWORK_SCANNING.md` - Comprehensive network scanning guide
  - Updated `README.md` with network scanning overview
  - Updated `INSTALL.md` with network scanning setup

### Changed
- `netbox-sync.py` - Integrated network scanning into main sync workflow
- `config.ini.example` - Added network scanning configuration section

### Technical Details
- Uses `ipaddress` module for network parsing and host enumeration
- Supports CIDR, range, and single host formats
- ThreadPoolExecutor for parallel network scanning (default 50 threads)
- Health checks on ports 443 and 80 for host discovery
- Automatic sampling for networks larger than /24
- Comprehensive logging with emoji status indicators

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

### From 1.1.0 to 1.2.0

1. Update your repository:
```bash
cd /opt/netbox-proxmox-sync
git pull origin main
```

2. New files:
   - `network_scanner.py` - Network scanning module
   - `network_scanning_integration.py` - Integration module

3. Update your config.ini with network scanning settings:
```ini
[network_scanning]
enabled = False  # Set to True to enable
# Networks to scan (comma-separated)
# Formats: 192.168.1.0/24 or 10.0.0.1-10.0.0.254
networks_to_scan = 192.168.1.0/24,10.0.0.0/8
ports_to_scan = 22,80,443,3306,5432,8080
timeout = 2
max_threads = 50
```

4. Test the new features:
```bash
python netbox-sync.py
```

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
python netbox-sync.py  # Will run with port scanning if enabled
```

---

## Known Limitations

- Network scanning requires network connectivity to target subnets
- Large networks (>254 hosts) are sampled to avoid long scan times
- Service creation in NetBox is logged but not yet persisted to database
- Socket-based scanning has timeout (configurable, default 2-5 seconds)
- Large port ranges (1-65535) will take significant time to scan
- No ICMP ping support - uses TCP health checks instead

---

## Future Enhancements

- [ ] ICMP ping support for host discovery
- [ ] Actual NetBox service/device creation API integration
- [ ] Service update/delete capabilities
- [ ] Per-VM/network port scanning profiles
- [ ] Service status monitoring
- [ ] Performance metrics and statistics
- [ ] Web UI dashboard
- [ ] Database backup and restore
- [ ] Vulnerability scanning integration
- [ ] Custom port/service mapping per network
