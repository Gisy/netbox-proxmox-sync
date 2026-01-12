# Installation & Setup Guide

## Prerequisites

- Python 3.7 or higher
- Access to Proxmox API (user with API token)
- Access to NetBox API (user with API token)
- Network connectivity to both Proxmox and NetBox
- (Optional) OPNsense for ARP table lookups

## Step 1: Clone Repository

```bash
git clone https://github.com/Gisy/netbox-proxmox-sync.git
cd netbox-proxmox-sync
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

- `requests` - HTTP library for API calls
- `proxmoxer` - Proxmox API wrapper
- `pynetbox` - NetBox API wrapper
- `python-dotenv` - Environment variable management

## Step 3: Create Configuration

Copy and edit the configuration file:

```bash
cp config.ini.example config.ini
```

### Proxmox Configuration

```ini
[proxmox]
pve_host = pve.example.com
pve_user = sync@pam
pve_password = your_password
pve_verify_ssl = False
netbox_site = Datacenter
```

**Get Proxmox credentials:**
1. Login to Proxmox Web UI
2. Datacenter → Users → Add User
3. Create user: `sync@pam`
4. Create API token in user's API tokens section
5. Copy token ID and secret

### NetBox Configuration

```ini
[netbox]
url = https://netbox.example.com
token = your_api_token
ssl_verify = True
```

**Get NetBox API token:**
1. Login to NetBox
2. Admin → Users and Permissions → Users
3. Create new user or use existing
4. Generate API token
5. Copy token to config

## Step 4: (Optional) Enable Port Scanning

Port scanning automatically detects open ports and creates services in NetBox.

### Quick Enable

```bash
# Edit config.ini
sed -i 's/enabled = False/enabled = True/' config.ini
```

### Manual Configuration

```ini
[port_scanning]
enabled = True
ports_to_scan = 22,80,443,3306,5432,8080,8443
timeout = 5
max_threads = 20
```

**Port Syntax:**
- Single: `22,80,443`
- Ranges: `1-1024,3000-3100`
- Mixed: `22,80,443,3000-3100`

See [PORT_SCANNING.md](PORT_SCANNING.md) for details.

## Step 5: Test Configuration

```bash
# Test Proxmox connection
python netbox-sync.py --test-proxmox

# Test NetBox connection
python netbox-sync.py --test-netbox

# Test OPNsense (if configured)
python netbox-sync.py --test-opnsense

# Run dry-run (no changes)
python netbox-sync.py --dry-run
```

## Step 6: Run Synchronization

### One-Time Sync

```bash
python netbox-sync.py
```

### Continuous Sync

```bash
# Background daemon
nohup python netbox-sync.py &

# Or with systemd service (see below)
```

### Port Scanning Only

```bash
# Scan all ports from config
python netbox-sync.py --scan

# Scan specific ports
python netbox-sync.py --scan --ports 22,80,443

# Custom timeout
python netbox-sync.py --scan --timeout 10
```

## Systemd Service (Optional)

Create `/etc/systemd/system/netbox-sync.service`:

```ini
[Unit]
Description=NetBox Proxmox Synchronization
After=network.target

[Service]
Type=simple
User=netbox-sync
WorkingDirectory=/home/netbox-sync/netbox-proxmox-sync
ExecStart=/usr/bin/python3 /home/netbox-sync/netbox-proxmox-sync/netbox-sync.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable netbox-sync
sudo systemctl start netbox-sync
sudo systemctl status netbox-sync
```

View logs:

```bash
sudo journalctl -u netbox-sync -f
```

## Cron Job (Alternative)

Add to crontab:

```bash
# Sync every hour
0 * * * * cd /path/to/netbox-proxmox-sync && python netbox-sync.py >> netbox-sync.log 2>&1

# Scan ports every 2 hours
0 */2 * * * cd /path/to/netbox-proxmox-sync && python netbox-sync.py --scan >> netbox-sync.log 2>&1
```

## Docker (Optional)

### Build Image

```bash
docker build -t netbox-proxmox-sync .
```

### Run Container

```bash
docker run -d \
  -v /path/to/config.ini:/app/config.ini \
  -v /path/to/logs:/app/logs \
  --name netbox-sync \
  netbox-proxmox-sync
```

## Troubleshooting

### Connection Issues

**Proxmox connection fails:**
```bash
# Check connectivity
ping pve.example.com

# Test API
curl -k https://pve.example.com:8006/api2/json/version

# Verify credentials in config.ini
```

**NetBox connection fails:**
```bash
# Check connectivity
ping netbox.example.com

# Test API
curl -H "Authorization: Token YOUR_TOKEN" \
  https://netbox.example.com/api/dcim/devices/

# Verify API token in config.ini
```

### Missing VMs in NetBox

1. Verify NetBox site matches `[proxmox] netbox_site` in config
2. Check NetBox API token has permissions
3. Verify Proxmox user can see all VMs:
   ```bash
   # On Proxmox
   pveum aclmod / -user sync@pam -role Administrator
   ```

### Port Scanning Issues

See [PORT_SCANNING.md](PORT_SCANNING.md) troubleshooting section.

## Uninstall

```bash
# Stop service
sudo systemctl stop netbox-sync
sudo systemctl disable netbox-sync

# Remove files
rm -rf /home/netbox-sync/netbox-proxmox-sync

# Or just:
cd .. && rm -rf netbox-proxmox-sync
```

## Next Steps

1. **Read [README.md](README.md)** for feature overview
2. **Check [QUICK-REFERENCE.md](QUICK-REFERENCE.md)** for CLI commands
3. **See [PORT_SCANNING.md](PORT_SCANNING.md)** for port scanning setup
4. **View logs** to monitor synchronization

## Support

- GitHub Issues: https://github.com/Gisy/netbox-proxmox-sync/issues
- Documentation: [README.md](README.md)
- Configuration: [config.ini.example](config.ini.example)

---

**Installation complete!** Run `python netbox-sync.py` to start syncing. 🚀
