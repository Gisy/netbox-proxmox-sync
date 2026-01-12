# Quick Reference - NetBox Proxmox Sync

## Installation (5 minutes)

```bash
# 1. Download files
mkdir netbox-sync && cd netbox-sync
# Place all files here

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp config.ini.example config.ini
nano config.ini  # Fill in credentials

# 4. Test
./netbox-sync.py --dry-run --debug

# 5. Run
./netbox-sync.py
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `./netbox-sync.py` | Run normal sync |
| `./netbox-sync.py --dry-run` | Test without changes |
| `./netbox-sync.py --debug` | Show detailed output |
| `./netbox-sync.py --no-arp` | Disable ARP lookup |
| `./netbox-sync.py --help` | Show help message |
| `./netbox-sync.py --version` | Show version |
| `./netbox-sync.py --config custom.ini` | Use custom config |

## Configuration Fields

### [proxmox]
```ini
host = 192.168.1.100
user = root@pam
token = sync-token
secret = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### [netbox]
```ini
url = https://netbox.example.com
token = abcdefghijklmnopqrstuvwxyz0123456789abcd
cluster_name = proxmox-prod
```

### [opnsense] (Optional)
```ini
url = https://opnsense.example.com
key = your-api-key
secret = your-api-secret
```

### [general]
```ini
verify_ssl = false
request_timeout = 10
retry_count = 3
```

## Common Issues & Solutions

### Issue: "Config not found"
**Solution:**
```bash
cp config.ini.example config.ini
```

### Issue: "Proxmox connection failed"
**Check:**
- Proxmox host is reachable: `ping proxmox.example.com`
- Credentials are correct in config.ini
- API token exists and is valid
- Firewall allows port 8006

**Debug:**
```bash
curl -k https://proxmox.example.com:8006/api2/json/nodes
```

### Issue: "NetBox 401 Unauthorized"
**Check:**
- Token is correct in config.ini
- Token hasn't expired
- Token has permission for:
  - Virtualization (VM, Cluster, Interface)
  - IPAM (IP Address)

**Solution:**
```bash
# Regenerate token in NetBox UI
# Admin → Authentication → Tokens → Add
```

### Issue: "No VMs/containers found"
**Check:**
- Proxmox user has read permissions
- VMs actually exist in Proxmox
- Firewall doesn't block API access

**Debug:**
```bash
./netbox-sync.py --debug --dry-run
```

### Issue: "OPNsense ARP error"
**Check:**
- OPNsense API is enabled
- API key/secret are correct
- Firewall allows API port access

**Solution:**
- Disable ARP lookup: `./netbox-sync.py --no-arp`
- Or fix OPNsense configuration

## Proxmox API Token Setup

1. **Web UI**: Datacenter → API Tokens
2. **Click**: "Add"
3. **User**: root@pam
4. **Token Name**: sync-token (or your choice)
5. **Privilege Separation**: ☐ Unchecked
6. **Expiration**: Set as needed
7. **Permissions**: (auto-assigned to root@pam)
8. **Note**: Token Secret shown only once!

## NetBox API Token Setup

1. **Web UI**: Admin → Authentication → Tokens
2. **Click**: "Add Token"
3. **User**: Your account
4. **Description**: "NetBox Proxmox Sync"
5. **Expiration**: Optional
6. **Click**: "Create"
7. **Copy**: Token immediately (can't view again!)
8. **Assign**: Permissions for Virtualization + IPAM

## Sync Output Example

```
======================================================================
Proxmox → NetBox Sync v1.0.0
======================================================================

✅ Proxmox: 192.168.1.100

Scanning 2 nodes...

 Node: pve1
 ✅ VM: vm-web-01 (4C, 8192MB, 100GB | MAC: 52:54:00:12:34:56 | IP: 192.168.1.50) [active]
 ↪ Interface eth0 at VM 15 exists (ID 123)
 ✅ IP 192.168.1.50 at IF 123 created (ID 456)
 ✅ VM ID 789 primary_ip4 -> IP-ID 456 (192.168.1.50)

 Node: pve2
 ✅ Ctr: ct-db-01 (2C, 4096MB, 50GB | MAC: 52:54:00:34:56:78 | IP: 192.168.1.51) [active]

======================================================================
✅ Total: 2 VMs/containers found
Synchronizing VMs/containers with NetBox:
----------------------------------------------------------------------
 ✅ vm-web-01 exists (ID 15)
 ✅ ct-db-01 created (ID 16)
----------------------------------------------------------------------

✅ 2/2 VMs/containers synchronized

📊 ARP entries found: 50
```

## Log Levels

```bash
# Normal (info only)
./netbox-sync.py

# Debug (detailed output)
./netbox-sync.py --debug

# Dry-run (test without changes)
./netbox-sync.py --dry-run --debug
```

## Cron Schedule Examples

### Every 5 minutes
```bash
*/5 * * * * /path/to/netbox-sync/netbox-sync.py >> /var/log/netbox-sync.log 2>&1
```

### Hourly
```bash
0 * * * * /path/to/netbox-sync/netbox-sync.py >> /var/log/netbox-sync.log 2>&1
```

### Every 6 hours
```bash
0 */6 * * * /path/to/netbox-sync/netbox-sync.py >> /var/log/netbox-sync.log 2>&1
```

### Daily at 2 AM
```bash
0 2 * * * /path/to/netbox-sync/netbox-sync.py >> /var/log/netbox-sync.log 2>&1
```

## Files Overview

| File | Purpose | Size |
|------|---------|------|
| netbox-sync.py | Main script | ~415 lines |
| common.py | Utilities & config | ~218 lines |
| nb_vm.py | VM management | ~237 lines |
| nb_interfaces.py | Interface handling | ~185 lines |
| nb_ip.py | IP management | ~191 lines |
| config.ini.example | Config template | ~46 lines |
| requirements.txt | Dependencies | ~4 lines |
| .gitignore | Git ignore rules | ~56 lines |

## Performance Tips

1. **Reduce frequency** if running into rate limits
2. **Disable ARP lookup** (`--no-arp`) if OPNsense is slow
3. **Use debug mode** only for troubleshooting
4. **Check firewall** for network delays
5. **Monitor logs** for performance issues

## Security Checklist

- [ ] config.ini is in .gitignore
- [ ] No credentials in environment
- [ ] API tokens have minimal required permissions
- [ ] SSL verification enabled in production
- [ ] Firewalls restrict API access
- [ ] Regular token rotation (optional)
- [ ] Logs don't contain sensitive data

## Getting Help

1. **Check** README-EN.md
2. **Read** INSTALL-EN.md
3. **Enable** debug mode: `--debug`
4. **Run** dry-run: `--dry-run`
5. **Review** configuration thoroughly
6. **Test** manually with curl/Postman

## Version Info

- **Current**: 1.0.0
- **Python**: 3.7+
- **License**: MIT
