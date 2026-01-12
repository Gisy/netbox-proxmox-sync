# Changelog - NetBox Proxmox Sync

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-01-12

### Added
- Initial release of NetBox Proxmox Sync
- Full VM and container synchronization from Proxmox to NetBox
- MAC address automatic detection and mapping
- IP address lookup via OPNsense ARP table
- Interface management (eth0, eth1, etc.)
- Status synchronization (active/offline)
- Dry-run mode for safe testing
- Debug logging support
- Configuration file support
- CLI interface with multiple options
- Comprehensive error handling and retries
- Python 3.7+ support

### Features
- **VM Sync**: Automatically discover and sync VMs from Proxmox
- **Container Sync**: Support for LXC containers
- **MAC Mapping**: Automatic MAC address detection
- **IP Lookup**: OPNsense ARP table integration for IP discovery
- **Interface Management**: Create and manage VM interfaces in NetBox
- **Status Tracking**: Monitor VM status (running/offline)
- **Resource Info**: Capture vCPU, memory, and disk information
- **Cluster Management**: Automatic cluster creation and management
- **Retry Logic**: Robust API call handling with retries
- **SSL Support**: Optional SSL verification for self-signed certs

### Security
- No hardcoded secrets or credentials
- Config file (config.ini) excluded from version control
- Token-based authentication
- SSL certificate validation (optional)
- Secure API communication

### Dependencies
- requests >= 2.28.0
- proxmoxer >= 1.3.0
- configparser >= 5.3.0
- python-dotenv >= 0.20.0

### Documentation
- README-EN.md - Quick start guide
- INSTALL-EN.md - Detailed installation instructions
- config-en.ini.example - Configuration template
- Inline code documentation

## Future Roadmap

### [1.1.0] - Planned
- [ ] Multiple cluster support
- [ ] Webhook integration for real-time sync
- [ ] Scheduled sync via daemon mode
- [ ] Database logging for sync history
- [ ] Email notifications on errors
- [ ] Web UI for configuration
- [ ] Metrics export (Prometheus format)
- [ ] Support for custom VM attributes

### [1.2.0] - Planned
- [ ] Two-way synchronization (NetBox → Proxmox)
- [ ] VM template management
- [ ] Storage pool tracking
- [ ] Network bridge management
- [ ] Custom field mapping
- [ ] Role-based access control

### [2.0.0] - Vision
- [ ] Kubernetes integration
- [ ] Multi-hypervisor support
- [ ] Advanced scheduling
- [ ] Machine learning for capacity planning
- [ ] Full REST API
- [ ] GraphQL support

## Known Issues

None reported yet.

## Support

For bug reports and feature requests, please create an issue or contact the maintainers.

## Contributors

- Project owner and maintainer
- Community contributions welcome

## License

MIT License - See LICENSE file for details
