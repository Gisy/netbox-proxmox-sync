# Network Scanning Guide

Network scanning allows you to discover and scan entire networks/subnets for active hosts and open ports.

## Features

### Network Discovery
- **CIDR Notation** - `192.168.1.0/24`, `10.0.0.0/8`, `172.16.0.0/16`
- **IP Ranges** - `192.168.1.1-192.168.1.254`, `10.0.0.1-10.0.0.254`
- **Single Hosts** - `192.168.1.100`, `8.8.8.8`

### Host Discovery
- TCP health checks on ports 443 and 80
- Multi-threaded discovery (up to 50 parallel threads)
- Automatic hostname resolution
- Smart sampling for large networks (/24+ automatically sampled)

### Port Scanning
- Multi-threaded TCP port scanning
- Configurable ports and port ranges
- Smart service name mapping (SSH, HTTP, MySQL, etc.)
- Comprehensive logging with emoji status indicators

## Configuration

### Enable Network Scanning

Edit `config.ini`:

```ini
[network_scanning]
# Enable network scanning feature
enabled = True

# Networks to scan (comma-separated)
# Format: CIDR notation (192.168.1.0/24) or IP ranges (10.0.0.1-10.0.0.254)
networks_to_scan = 192.168.1.0/24,10.0.0.0/8,172.16.0.100

# Ports to scan (comma-separated or ranges)
ports_to_scan = 22,80,443,3306,5432,8080-8090

# Socket timeout per host/port in seconds
timeout = 2

# Maximum parallel scanning threads
max_threads = 50
```

## Network Format Examples

### CIDR Notation
```ini
networks_to_scan = 192.168.1.0/24       # Scans 254 hosts
networks_to_scan = 10.0.0.0/16          # Scans 65534 hosts (will be sampled)
networks_to_scan = 172.16.5.0/25        # Scans 126 hosts
```

### IP Ranges
```ini
networks_to_scan = 192.168.1.1-192.168.1.254
networks_to_scan = 10.0.0.1-10.0.0.50,10.0.0.100-10.0.0.150
```

### Mixed Formats
```ini
networks_to_scan = 192.168.1.0/24,10.0.0.1-10.0.0.254,172.16.5.100
```

## Port Format Examples

### Individual Ports
```ini
ports_to_scan = 22,80,443,3306,5432
```

### Port Ranges
```ini
ports_to_scan = 22,80,443,8000-8100,9000-9010
```

### Mixed
```ini
ports_to_scan = 22,80,443,3000-3100,5432,8080-8090
```

## Usage

### Run with Network Scanning Enabled

```bash
python netbox-sync.py
```

The script will:
1. Sync known VMs from Proxmox
2. Scan port on known VMs
3. Discover hosts in configured networks
4. Scan ports on discovered hosts

### Output Example

```
🌐 Network Scanning Integration Starting...

🔍 Network Scanning:
Scanning 2 network(s)...
Scanning ports: [22, 80, 443, 3306, 5432, 8080]...

Added network: 192.168.1.0/24
Added range: 10.0.0.0/8
Scanning 300 hosts for availability...
  ✅ Host 192.168.1.100 is active
  ✅ Host 192.168.1.101 is active
  ✅ Host 10.0.0.50 is active

Found 3 active hosts

Scanning 192.168.1.100...
  Found 3 open ports: [22, 80, 443]
  ✅ Port 22 OPEN on 192.168.1.100
  ✅ Port 80 OPEN on 192.168.1.100
  ✅ Port 443 OPEN on 192.168.1.100
```

## Performance Considerations

### Network Sampling
- Networks smaller than /24 (256 hosts) - scanned fully
- Networks /24 to /16 - sampled (approx 100 hosts)
- Networks /16 or larger - heavily sampled (approx 100 hosts)

### Threading
- Host discovery: 50 parallel threads (default)
- Port scanning: 20 parallel threads per host (default)
- Total concurrent connections: Host Threads + (Hosts × Port Threads)

### Timeouts
- Default: 2 seconds per host/port
- Recommended: 2-5 seconds depending on network latency
- Increase for high-latency networks

### Examples
```ini
# Fast scan (small network, local)
timeout = 1
max_threads = 100

# Standard scan (medium network)
timeout = 2
max_threads = 50

# Thorough scan (large network, remote)
timeout = 5
max_threads = 30
```

## Port Service Mapping

Automatically detected services:

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

## Troubleshooting

### No hosts discovered
- Check network is reachable
- Check firewall allows TCP ports 443 and 80
- Try smaller network range for testing

### Scanning is slow
- Reduce `max_threads` (uses less CPU/connections)
- Increase `timeout` only if necessary
- Use smaller network ranges

### Errors in log
- `Invalid network X` - Check CIDR/range format
- `Host X timeout` - Network latency, increase timeout
- `Port X check failed` - Normal, just couldn't connect

## Integration with NetBox

Currently, discovered hosts and services are **logged but not persisted** to NetBox.

Future versions will support:
- Automatic device creation in NetBox
- Automatic service/port creation
- Device status tracking
- Service monitoring

## Examples

### Scan Office Network
```ini
[network_scanning]
enabled = True
networks_to_scan = 192.168.1.0/24
ports_to_scan = 22,80,443,3306,5432
timeout = 2
max_threads = 50
```

### Scan Multiple Sites
```ini
[network_scanning]
enabled = True
networks_to_scan = 192.168.1.0/24,192.168.2.0/24,10.0.0.0/16
ports_to_scan = 22,80,443,8000-9000
timeout = 3
max_threads = 50
```

### Scan Specific Ranges
```ini
[network_scanning]
enabled = True
networks_to_scan = 192.168.1.1-192.168.1.50,192.168.1.100-192.168.1.150
ports_to_scan = 22,80,443,3306
timeout = 2
max_threads = 30
```

## See Also

- [README.md](README.md) - Main documentation
- [PORT_SCANNING.md](PORT_SCANNING.md) - VM port scanning guide
- [INSTALL.md](INSTALL.md) - Installation instructions
