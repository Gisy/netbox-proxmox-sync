# NetBox Proxmox Sync v1.0.0

**Intelligent synchronization of Proxmox VMs to NetBox DCIM**

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp config.ini.example config.ini
nano config.ini  # Fill in Proxmox & NetBox credentials
```

### 3. Test (Safe!)
```bash
./netbox-sync.py --dry-run --debug
```

### 4. Production
```bash
./netbox-sync.py
```

## ✨ Features

- ✅ Automatically sync VMs/containers from Proxmox to NetBox
- ✅ Synchronize MAC addresses
- ✅ Fetch IPs via OPNsense ARP lookup
- ✅ Interface management
- ✅ Dry-run mode for testing
- ✅ Robust error handling
- ✅ CLI interface

## 📋 CLI Commands

```bash
./netbox-sync.py                    # Normal sync
./netbox-sync.py --dry-run          # Test without changes
./netbox-sync.py --debug            # Debug output
./netbox-sync.py --no-arp           # Without OPNsense
./netbox-sync.py --help             # Help
./netbox-sync.py --version          # Version
```

## 🐛 Troubleshooting

### "Config not found"
```bash
cp config.ini.example config.ini
```

### "Proxmox connection failed"
- Check host, user, token in config.ini
- Test: `curl -k https://proxmox.example.com/api/api2/json/nodes`

### "NetBox 401 Unauthorized"
- Check NetBox token
- Check permissions (Virtualization, IPAM)

## 📚 Files

| File | Content |
|------|---------|
| `netbox-sync.py` | Main script |
| `common.py` | Utilities |
| `nb_vm.py` | VM management |
| `nb_interfaces.py` | Interface management |
| `nb_ip.py` | IP management |
| `config.ini.example` | Config template |

## 🔐 Security

- ✅ No secrets in code
- ✅ Config in .gitignore
- ✅ SSL optional
- ✅ Token validation

## 📞 Support

For issues:
1. Read the logs: `tail -f /var/log/netbox-sync.log`
2. Use debug mode: `./netbox-sync.py --debug --dry-run`
3. Check config.ini

## 📄 License

MIT License
