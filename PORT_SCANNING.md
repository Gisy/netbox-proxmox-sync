# Port Scanning Feature

## Overview

NetBox Proxmox Sync includes an optional **port scanning feature** that automatically:

1. **Scans open ports** on all VMs and containers
2. **Creates services** in NetBox for detected ports
3. **Uses threading** for efficient parallel scanning
4. **Runs with configurable intervals**

## How It Works

```
Proxmox VM/Container
        ↓
   Port Scan (Socket)
        ↓
   Detect Open Ports
   (22, 80, 443, 3306, etc.)
        ↓
   Create Services in NetBox
   (auto-tcp-22, auto-tcp-80, etc.)
        ↓
   ✅ Services visible in NetBox UI
```

## Configuration

### Enable Port Scanning

Edit `config.ini`:

```ini
[port_scanning]
enabled = True
ports_to_scan = 22,80,443,3306,5432,8080,8443
timeout = 5
max_threads = 20
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | False | Enable/disable port scanning |
| `ports_to_scan` | 22,80,443,... | Comma-separated ports or ranges |
| `timeout` | 5 | Socket timeout per port (seconds) |
| `max_threads` | 20 | Max parallel scan threads |

### Port Syntax

```ini
# Single ports
ports_to_scan = 22,80,443

# Ranges
ports_to_scan = 1-1000,3000-3999,8000-9000

# Mixed
ports_to_scan = 22,80,443,3000-3100,8080-8090
```

## Usage

### Manual Scan

```bash
# Basic scan (uses config.ini)
python netbox-sync.py --scan

# Scan specific ports
python netbox-sync.py --scan --ports 22,80,443

# Scan with custom timeout
python netbox-sync.py --scan --timeout 10
```

### Automatic Scanning

Port scanning runs automatically when:

1. `enabled = True` in config
2. Regular sync runs (every `interval` seconds)
3. Or explicitly called with `--scan`

### Integration with Sync

The port scanning is integrated into the main sync:

```bash
# Sync VMs AND scan ports
python netbox-sync.py
```

## Performance

### Threading Model

- **Socket timeout**: 5 seconds per port (configurable)
- **Max threads**: 20 concurrent (configurable)
- **Scan performance**: ~4 ports per second with 20 threads

### Example Timings

For a network with 10 hosts scanning 50 ports each:

- Total ports: 500
- Estimated time: ~2 minutes (with 20 threads, 5s timeout)
- Hosts scanned in parallel ✅

### Optimization Tips

1. **Reduce ports**: Scan only essential ports
2. **Increase timeout**: Use 10s for unreliable networks
3. **Adjust threads**: More threads = faster but more CPU
4. **Disable when not needed**: Set `enabled = False`

## Examples

### Example 1: Scan Common Web Ports

```ini
[port_scanning]
enabled = True
ports_to_scan = 80,443,8080,8443
timeout = 5
```

### Example 2: Full Range Scan (Slow!)

```ini
[port_scanning]
enabled = True
ports_to_scan = 1-1024
timeout = 3
max_threads = 50
```

⚠️ **Warning**: Full range scan takes very long (1024+ ports × timeout)

### Example 3: Development Environment

```ini
[port_scanning]
enabled = True
ports_to_scan = 22,80,443,3000-3100,5000-5100,8000-9000
timeout = 2
max_threads = 30
```

## NetBox Service Structure

Scanned ports are created as **Services** in NetBox:

```
Service Name: auto-tcp-22
├── Protocol: TCP
├── Port: 22
├── Description: SSH - Auto-detected
└── Linked to: IP Address / Device

Service Name: auto-tcp-80
├── Protocol: TCP
├── Port: 80
├── Description: HTTP - Auto-detected
└── Linked to: IP Address / Device
```

View in NetBox:
- **IPAM** → **Services** → Filter by "auto-"

## Troubleshooting

### Services Not Appearing

1. Check if port scanning is enabled:
   ```bash
   grep "enabled" config.ini
   ```

2. Check logs:
   ```bash
   tail -f netbox-sync.log
   ```

3. Verify NetBox API token has write permissions

### Slow Scanning

1. Reduce port count:
   ```ini
   ports_to_scan = 22,80,443
   ```

2. Increase timeout:
   ```ini
   timeout = 3
   ```

3. Reduce threads:
   ```ini
   max_threads = 10
   ```

### Connection Errors

1. Check network connectivity:
   ```bash
   ping <vm_ip>
   ```

2. Verify firewall allows outbound connections

3. Check firewall rules on target VMs

## Port Mapping

Common ports automatically mapped to service names:

| Port | Service | Port | Service |
|------|---------|------|---------|
| 22 | SSH | 3306 | MySQL |
| 80 | HTTP | 5432 | PostgreSQL |
| 443 | HTTPS | 8080 | HTTP-Proxy |
| 25 | SMTP | 9200 | Elasticsearch |
| 53 | DNS | 27017 | MongoDB |
| 110 | POP3 | 6379 | Redis |
| 143 | IMAP | 5900 | VNC |
| 445 | SMB | 3389 | RDP |

See `port_scanner.py` for complete mapping.

## API Integration

### Programmatic Usage

```python
from port_scanner import PortScanner
from port_scanning_integration import PortScanningIntegration

# Initialize
scanner = PortScanner(timeout=5, max_threads=20)

# Scan single host
results = scanner.scan_ports("192.168.1.10", [22, 80, 443])
# Output: {22: True, 80: False, 443: True}

# Get open ports
open_ports = scanner.get_open_ports(results)
# Output: [22, 443]

# Get service names
print(scanner.get_service_name(22))  # Output: SSH
print(scanner.get_service_name(3000))  # Output: Service-3000
```

### Integration with Custom Scripts

```python
from port_scanning_integration import PortScanningIntegration
import pynetbox

# Setup
netbox = pynetbox.api('https://netbox.example.com', token='token')
integration = PortScanningIntegration(
    netbox_api=netbox,
    netbox_url='https://netbox.example.com',
    netbox_token='token'
)

# Scan and sync
integration.sync_vm_services(
    vm_name='vm-web-01',
    ip_address='192.168.1.50',
    ports=[22, 80, 443, 8080]
)
```

## Limitations

- ✅ TCP only (no UDP scanning yet)
- ✅ Requires network connectivity from scanning host
- ✅ Socket-based (not NMAP-based)
- ✅ Services created globally, linked to IP/Device
- ✅ Port timeout is global (no per-port timeout)

## Future Enhancements

Planned features:

- [ ] UDP port scanning
- [ ] Service version detection
- [ ] Custom service templates
- [ ] Scheduled scans
- [ ] Scan history/analytics
- [ ] Integration with Shodan/VirusTotal

---

**Need help?** Check [QUICK-REFERENCE.md](QUICK-REFERENCE.md) or open an issue on GitHub.
