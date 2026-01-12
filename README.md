# NetBox Proxmox Sync

**Intelligent synchronization of Proxmox VMs and containers to NetBox DCIM with optional port scanning.**

Automatically syncs your Proxmox infrastructure to NetBox with:
- ✅ VM and container data
- ✅ MAC address detection
- ✅ IP address lookup
- ✅ **Open port detection** (optional)
- ✅ Service management

## Features

### Core Synchronization
- **Automatic VM/Container Sync** - Syncs all VMs and containers from Proxmox to NetBox
- **MAC Address Detection** - Automatically detects and updates MAC addresses
- **IP Lookup** - Retrieves IP addresses via OPNsense ARP or NetBox IPAM
- **Status Management** - Tracks VM status (running, stopped, suspended)
- **Interface Tracking** - Monitors network interfaces and their status

### Port Scanning (NEW!)
- **Socket-Based Scanning** - Lightweight TCP port scanning without external tools
- **Multi-Threading** - Scan multiple ports and hosts in parallel (20 threads default)
- **Auto Service Creation** - Automatically create services in NetBox for open ports
- **Configurable Ports** - Scan specific ports or ranges (22, 80, 443, 3000-3100, etc.)
- **Smart Service Names** - Auto-map ports to service names (SSH, HTTP, MySQL, etc.)

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Gisy/netbox-proxmox-sync.git
cd netbox-proxmox-sync

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.ini.example config.ini
nano config.ini
```

### Configuration (config.ini)

**Minimal setup:**

```ini
[proxmox]
pve_host = pve.example.com
pve_user = sync@pam
pve_password = your_password
pve_verify_ssl = False
netbox_site = Datacenter

[netbox]
url = https://netbox.example.com
token = your_api_token
ssl_verify = True

[port_scanning]
enabled = False
```

### Run Synchronization

```bash
# One-time sync
python netbox-sync.py

# With port scanning
python netbox-sync.py --scan

# Specific ports
python netbox-sync.py --scan --ports 22,80,443
```

## Port Scanning Feature

Automatically detect open ports and create services in NetBox!

### Enable Port Scanning

```ini
[port_scanning]
enabled = True
ports_to_scan = 22,80,443,3306,5432,8080-8090
timeout = 5
max_threads = 20
```

### Usage Examples

```bash
# Scan with config defaults
python netbox-sync.py --scan

# Scan specific ports
python netbox-sync.py --scan --ports 22,80,443,3000-3100

# Custom timeout
python netbox-sync.py --scan --timeout 10

# Full sync + scanning
python netbox-sync.py
```

### Service Creation

Detected ports are created in NetBox as **Services**:

```
Service: auto-tcp-22
├── Protocol: TCP
├── Port: 22
├── Description: SSH - Auto-detected
└── Linked to: IP Address

Service: auto-tcp-80
├── Protocol: TCP
├── Port: 80
├── Description: HTTP - Auto-detected
└── Linked to: IP Address
```

### Port Mapping

Common ports are automatically mapped to service names:

| Port | Service | Port | Service |
|------|---------|------|---------|
| 22 | SSH | 3306 | MySQL |
| 80 | HTTP | 5432 | PostgreSQL |
| 443 | HTTPS | 8080 | HTTP-Proxy |
| 25 | SMTP | 9200 | Elasticsearch |
| 53 | DNS | 6379 | Redis |
| 110 | POP3 | 5900 | VNC |
| 143 | IMAP | 3389 | RDP |
| 445 | SMB | 27017 | MongoDB |

See [PORT_SCANNING.md](PORT_SCANNING.md) for complete documentation.

## Architecture

```
Proxmox Cluster
    ↓
netbox-sync.py (Main Script)
    ├── nb_vm.py (VM Management)
    ├── nb_interfaces.py (Network Interfaces)
    ├── nb_ip.py (IP Addresses)
    ├── nb_services.py (Services/Ports) [NEW]
    ├── port_scanner.py (Port Scanning) [NEW]
    └── common.py (Utilities)
    ↓
NetBox DCIM
    └── Devices, Interfaces, IP Addresses, Services
```

## Files

### Core Scripts
- `netbox-sync.py` - Main synchronization script
- `common.py` - Common utilities and helpers
- `nb_vm.py` - VM and container management
- `nb_interfaces.py` - Network interface management
- `nb_ip.py` - IP address management

### Port Scanning (NEW)
- `port_scanner.py` - Socket-based port scanning with threading
- `nb_services.py` - NetBox service management
- `port_scanning_integration.py` - Integration with main sync

### Configuration & Documentation
- `config.ini.example` - Configuration template
- `requirements.txt` - Python dependencies
- `README.md` - This file
- `INSTALL.md` - Installation guide
- `QUICK-REFERENCE.md` - CLI reference
- `PORT_SCANNING.md` - Port scanning guide
- `CHANGELOG.md` - Version history

## CLI Commands

### Synchronization

```bash
# Full sync
python netbox-sync.py

# Dry-run (no changes)
python netbox-sync.py --dry-run

# Continuous sync
python netbox-sync.py --loop
```

### Port Scanning

```bash
# Scan all ports from config
python netbox-sync.py --scan

# Scan specific ports
python netbox-sync.py --scan --ports 22,80,443

# Custom timeout
python netbox-sync.py --scan --timeout 10
```

### Testing

```bash
# Test Proxmox connection
python netbox-sync.py --test-proxmox

# Test NetBox connection
python netbox-sync.py --test-netbox

# Test OPNsense connection
python netbox-sync.py --test-opnsense
```

### Other Options

```bash
# Verbose logging
python netbox-sync.py --verbose

# Debug mode
python netbox-sync.py --debug

# Show help
python netbox-sync.py --help
```

See [QUICK-REFERENCE.md](QUICK-REFERENCE.md) for complete command reference.

## Configuration

### Basic Setup

1. Copy `config.ini.example` to `config.ini`
2. Set Proxmox credentials and URL
3. Set NetBox URL and API token
4. Set NetBox site name matching your Proxmox cluster location

### Advanced Options

```ini
[proxmox]
pve_host = pve.example.com
pve_user = sync@pam
pve_password = your_password
pve_verify_ssl = False
netbox_site = Datacenter

[netbox]
url = https://netbox.example.com
token = your_api_token
ssl_verify = True

[sync]
enabled = True
interval = 3600
dry_run = False

[port_scanning]
enabled = False
ports_to_scan = 22,80,443,3306,5432,8080-8090
timeout = 5
max_threads = 20

[logging]
level = INFO
file = netbox-sync.log
max_size = 10
backup_count = 5
```

See [INSTALL.md](INSTALL.md) for detailed setup instructions.

## Performance

### Synchronization
- **VM Sync**: ~2 seconds per VM
- **IP Lookup**: ~1 second per VM (via ARP or NetBox)
- **Full Sync**: <1 minute for typical deployment (10-20 VMs)

### Port Scanning
- **Per Host**: ~2 minutes for 50 ports with 20 threads, 5s timeout
- **Multiple Hosts**: Scanned in parallel
- **Memory**: ~50 MB for 20 concurrent threads

## Requirements

- Python 3.7+
- Network access to Proxmox API
- Network access to NetBox API
- (Optional) Network access to OPNsense for ARP lookups

### Dependencies

```
requests >= 2.28.0
proxmoxer >= 1.3.0
pynetbox >= 7.0.0
python-dotenv >= 0.20.0
configparser >= 5.3.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Troubleshooting

### Connection Issues

```bash
# Test Proxmox
curl -k https://pve.example.com:8006/api2/json/version

# Test NetBox
curl -H "Authorization: Token YOUR_TOKEN" \
  https://netbox.example.com/api/dcim/devices/
```

### Logging

Check logs for detailed error messages:
```bash
tail -f netbox-sync.log
```

### Debug Mode

```bash
python netbox-sync.py --debug
```

See [INSTALL.md](INSTALL.md) for troubleshooting guide.

## Development

### Code Structure

```
netbox-proxmox-sync/
├── netbox-sync.py           # Main entry point
├── common.py                # Shared utilities
├── nb_vm.py                 # VM management
├── nb_interfaces.py         # Interface management
├── nb_ip.py                 # IP management
├── nb_services.py           # Service management [NEW]
├── port_scanner.py          # Port scanning [NEW]
├── port_scanning_integration.py  # Integration [NEW]
├── config.ini.example       # Config template
├── requirements.txt         # Dependencies
├── README.md                # This file
├── INSTALL.md               # Installation guide
├── QUICK-REFERENCE.md       # CLI reference
├── PORT_SCANNING.md         # Port scanning guide
├── CHANGELOG.md             # Version history
└── .gitignore               # Git ignore rules
```

### Adding Features

1. Create new module (e.g., `nb_newfeature.py`)
2. Add to main script with proper error handling
3. Update documentation
4. Test thoroughly
5. Create pull request

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch
3. Test changes
4. Submit pull request

## License

MIT License - See LICENSE file for details

## Support

- **Documentation**: [INSTALL.md](INSTALL.md) | [QUICK-REFERENCE.md](QUICK-REFERENCE.md) | [PORT_SCANNING.md](PORT_SCANNING.md)
- **Issues**: https://github.com/Gisy/netbox-proxmox-sync/issues
- **Discussions**: https://github.com/Gisy/netbox-proxmox-sync/discussions

## Version

**1.0.0** - 2026-01-12

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

**NetBox Proxmox Sync** - Keep your infrastructure in sync! 🚀
