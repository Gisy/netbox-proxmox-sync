# Installation Guide - NetBox Proxmox Sync

## Prerequisites

- Python 3.7+
- pip (Python package manager)
- Access to Proxmox cluster
- Access to NetBox instance
- (Optional) OPNsense firewall with API access

## Step-by-Step Installation

### 1. Clone or Download Project

```bash
# Create project directory
mkdir netbox-sync
cd netbox-sync

# Place all files here:
# - netbox-sync.py
# - common.py
# - nb_vm.py
# - nb_interfaces.py
# - nb_ip.py
# - requirements.txt
# - config.ini.example
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` - HTTP library
- `proxmoxer` - Proxmox API client
- `configparser` - Config file parsing

### 4. Configure the Script

```bash
# Copy example configuration
cp config.ini.example config.ini

# Edit with your credentials
nano config.ini
```

**Required fields:**

**[proxmox]**
- `host`: Your Proxmox host (e.g., `192.168.1.100`)
- `user`: Proxmox user (e.g., `root@pam`)
- `token`: API token name
- `secret`: API token secret

To create a Proxmox API token:
1. Go to Proxmox Web UI → Datacenter → API Tokens
2. Click "Add"
3. Ensure "Privilege Separation" is unchecked
4. Note the token name and secret

**[netbox]**
- `url`: NetBox URL (e.g., `https://netbox.example.com`)
- `token`: NetBox API token
- `cluster_name`: Name for your cluster in NetBox

To create a NetBox API token:
1. Go to NetBox Web UI → Admin → Authentication → Tokens
2. Click "Add Token"
3. Set expiration or leave empty for no expiration
4. Copy the token immediately (you can't view it again)

**[opnsense]** (Optional)
- `url`: OPNsense firewall URL
- `key`: API key
- `secret`: API secret

### 5. Make Script Executable

```bash
chmod +x netbox-sync.py
```

### 6. Test the Installation

```bash
# Test without making changes (dry-run)
./netbox-sync.py --dry-run --debug

# Or with Python:
python3 netbox-sync.py --dry-run --debug
```

Expected output:
```
======================================================================
Proxmox → NetBox Sync v1.0.0
======================================================================

✅ Proxmox: proxmox.example.com

Scanning 2 nodes...

 Node: pve1
 ✅ VM: vm-01 (4C, 8192MB, 100GB | MAC: 52:54:00:12:34:56 | IP: 192.168.1.100) [active]
 DRY-RUN: VM vm-01 (VMID 100) net0 → eth0 | MAC: 52:54:00:12:34:56 | IP: 192.168.1.100

✅ Total: 1 VMs/containers found
```

### 7. Run the Sync

```bash
./netbox-sync.py
```

This will:
1. Connect to Proxmox
2. Fetch all VMs and containers
3. Create/update them in NetBox
4. Synchronize MAC addresses
5. Fetch IP addresses (if OPNsense configured)

### 8. Schedule Regular Syncs (Optional)

Add to crontab to run every 5 minutes:

```bash
crontab -e

# Add this line:
*/5 * * * * /path/to/netbox-sync/netbox-sync.py > /var/log/netbox-sync.log 2>&1
```

## Troubleshooting

### "Config not found"
```bash
# Make sure config.ini exists in the same directory
ls -la config.ini
cp config.ini.example config.ini  # If missing
```

### "proxmoxer not installed"
```bash
pip install -r requirements.txt
```

### "Proxmox connection failed"
- Check firewall allows connection to Proxmox port (usually 8006)
- Verify credentials in config.ini
- Test connection:
  ```bash
  curl -k -X GET https://your-proxmox:8006/api2/json/nodes \
    -H "Authorization: PVEAPIToken=user@realm!token_name=secret"
  ```

### "NetBox 401 Unauthorized"
- Verify NetBox token is correct
- Check token has permissions for:
  - Virtualization (read/write)
  - IPAM (read/write)
- Try regenerating the token

### "No VMs/containers found"
- Check Proxmox user has read permissions
- Verify VMs exist in Proxmox
- Check debug output: `./netbox-sync.py --debug --dry-run`

## Next Steps

1. **Review logs** from dry-run to verify configuration
2. **Run sync** once manually: `./netbox-sync.py`
3. **Verify** in NetBox that VMs appear correctly
4. **Schedule** regular syncs (cron) for automatic updates
5. **Monitor** logs for issues: `tail -f /var/log/netbox-sync.log`

## Getting Help

1. Check the README-EN.md for features and options
2. Enable debug mode: `./netbox-sync.py --debug`
3. Review configuration thoroughly
4. Check API token permissions
5. Test connectivity manually with curl

## Uninstall

```bash
rm -rf netbox-sync
# Or if using virtual environment:
rm -rf venv
```
