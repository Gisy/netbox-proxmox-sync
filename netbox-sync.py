#!/usr/bin/env python3

"""
NetBox ↔ Proxmox Sync - Synchronize Proxmox VMs/Containers to NetBox

Features:
- Automatic VM and container synchronization
- MAC address detection and IP lookup (via OPNsense ARP)
- Optional port scanning on known VMs
- Optional network scanning and discovery with NetBox device creation
- Automatic duplicate prevention (device name & IP address checks)
- Comprehensive logging with emoji status indicators
"""

import sys
import logging
import configparser
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from nb_vm import get_or_create_vm
import requests
from proxmoxer import ProxmoxAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings()


def load_config() -> Dict:
    """Load configuration from config.ini"""
    config_file = Path(__file__).parent / 'config.ini'
    
    if not config_file.exists():
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    return {
        # Proxmox
        'PVE_HOST': config.get('proxmox', 'host'),
        'PVE_USER': config.get('proxmox', 'user'),
        'PVE_TOKEN': config.get('proxmox', 'token'),
        'PVE_SECRET': config.get('proxmox', 'secret'),
        'PVE_VERIFY_SSL': config.getboolean('proxmox', 'verify_ssl', fallback=False),
        
        # NetBox
        'NB_URL': config.get('netbox', 'url'),
        'NB_TOKEN': config.get('netbox', 'token'),
        'CLUSTER_NAME': config.get('netbox', 'cluster_name'),
        'NB_VERIFY_SSL': config.getboolean('netbox', 'ssl_verify', fallback=True),
        
        # OPNsense (optional)
        'OPNSENSE_URL': config.get('opnsense', 'url', fallback=''),
        'OPNSENSE_KEY': config.get('opnsense', 'key', fallback=''),
        'OPNSENSE_SECRET': config.get('opnsense', 'secret', fallback=''),
        
        # Port Scanning
        'PORT_SCANNING_ENABLED': config.getboolean('port_scanning', 'enabled', fallback=False),
        'PORT_SCANNING_PORTS': config.get('port_scanning', 'ports_to_scan', fallback='22,80,443'),
        'PORT_SCANNING_TIMEOUT': config.getint('port_scanning', 'timeout', fallback=5),
        'PORT_SCANNING_THREADS': config.getint('port_scanning', 'max_threads', fallback=20),
        
        # Network Scanning
        'NETWORK_SCANNING_ENABLED': config.getboolean('network_scanning', 'enabled', fallback=False),
        'NETWORK_SCANNING_NETWORKS': config.get('network_scanning', 'networks_to_scan', fallback=''),
        'NETWORK_SCANNING_PORTS': config.get('network_scanning', 'ports_to_scan', fallback='22,80,443'),
        'NETWORK_SCANNING_TIMEOUT': config.getint('network_scanning', 'timeout', fallback=2),
        'NETWORK_SCANNING_THREADS': config.getint('network_scanning', 'max_threads', fallback=50),
    }


# Load configuration
config = load_config()

# Create sessions
session = requests.Session()
session.verify = config['NB_VERIFY_SSL']

# OPNsense session (optional)
opn_session = None
if config['OPNSENSE_URL'] and config['OPNSENSE_KEY']:
    opn_session = requests.Session()
    opn_session.auth = (config['OPNSENSE_KEY'], config['OPNSENSE_SECRET'])
    opn_session.verify = False
    logger.info("✅ OPNsense ARP lookup enabled\n")


def parse_ports_from_string(ports_str: str) -> List[int]:
    """
    Parse port string: 22,80,443 or 22,80,443,3000-3100
    
    Args:
        ports_str: Port string
        
    Returns:
        Sorted list of unique ports
    """
    ports = []
    try:
        for part in ports_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ports.extend(range(int(start), int(end) + 1))
            else:
                ports.append(int(part))
        return sorted(list(set(ports)))
    except Exception as e:
        logger.warning(f"Failed to parse ports: {e}")
        return [22, 80, 443]


def extract_disk_size(disk_str: str) -> int:
    """Extract disk size from disk string (e.g., 'virtio0: local:100'"""
    try:
        if 'size=' in disk_str:
            size_part = disk_str.split('size=')[1].split(',')[0]
            if size_part.endswith('G'):
                return int(size_part[:-1])
            elif size_part.endswith('M'):
                return int(size_part[:-1]) // 1024
            elif size_part.endswith('T'):
                return int(size_part[:-1]) * 1024
    except:
        pass
    return 0


def get_vm_mac(vm_config: Dict, net_index: int) -> Optional[str]:
    """Extract MAC address from VM/Container config"""
    try:
        net_key = f'net{net_index}'
        if net_key not in vm_config:
            return None
        
        net_str = vm_config[net_key]
        for part in net_str.split(','):
            if '=' in part:
                _, mac_candidate = part.split('=', 1)
                mac_candidate = mac_candidate.strip()
                if len(mac_candidate) == 17 and mac_candidate.count(':') == 5:
                    return mac_candidate.lower()
    except:
        pass
    return None


def fetch_arp_map() -> Dict[str, str]:
    """Fetch ARP table from OPNsense (MAC -> IP mapping)"""
    if not opn_session:
        return {}
    
    try:
        url = f"{config['OPNSENSE_URL']}/api/diagnostics/interface/get_arp"
        r = opn_session.get(url, timeout=10)
        r.raise_for_status()
        
        data = r.json()
        rows = data if isinstance(data, list) else data.get('rows', [])
        
        arp_map = {}
        for row in rows:
            ip = row.get('ip') or row.get('ipaddr')
            mac = row.get('mac') or row.get('macaddr')
            if ip and mac:
                arp_map[mac.lower()] = ip
        
        logger.debug(f"OPNsense ARP: {len(arp_map)} entries")
        return arp_map
    except Exception as e:
        logger.warning(f"⚠️ OPNsense ARP Error: {e}")
        return {}


def get_ip_from_mac(mac: str, arp_map: Dict[str, str]) -> Optional[str]:
    """Get IP address for MAC from ARP table"""
    if not mac or not arp_map:
        return None
    
    return arp_map.get(mac.lower())


def get_proxmox_vms(api) -> List[Dict]:
    """Get all VMs and containers from Proxmox"""
    arp_map = fetch_arp_map()
    vms: List[Dict] = []
    
    try:
        nodes = api.nodes.get()
        logger.info(f"Scanning {len(nodes)} nodes...\n")
        
        for node in nodes:
            node_name = node['node']
            logger.info(f" Node: {node_name}")
            
            # ===== QEmu VMs =====
            try:
                qemu = api.nodes(node_name).qemu.get()
                for vm in qemu:
                    try:
                        vm_config = api.nodes(node_name).qemu(vm['vmid']).config.get()
                        disk_gb = 0
                        
                        for disk_key in ['virtio0', 'scsi0', 'sata0', 'ide0', 'virtio1', 'scsi1']:
                            if disk_key in vm_config:
                                disk_gb = extract_disk_size(vm_config[disk_key])
                                if disk_gb > 0:
                                    break
                        
                        mac_addr = get_vm_mac(vm_config, 0)
                        ip_addr = get_ip_from_mac(mac_addr, arp_map) if mac_addr else None
                        status = 'active' if vm['status'] == 'running' else 'offline'
                        
                        vm_data = {
                            'name': vm['name'],
                            'vmid': vm['vmid'],
                            'type': 'vm',
                            'node': node_name,
                            'vcpus': vm_config.get('cores', 1),
                            'memory_mb': vm_config.get('memory', 512),
                            'disk_gb': disk_gb,
                            'mac_addr': mac_addr,
                            'ip_addr': ip_addr,
                            'status': status,
                            'description': f"Type: VM | VMID: {vm['vmid']} | Node: {node_name} | MAC: {mac_addr or 'N/A'}",
                        }
                        
                        vms.append(vm_data)
                        
                        mac_str = f" | MAC: {mac_addr}" if mac_addr else ""
                        ip_str = f" | IP: {ip_addr}" if ip_addr else ""
                        logger.info(
                            f" ✅ VM: {vm['name']} "
                            f"({vm_data['vcpus']}C, {vm_data['memory_mb']}MB, {disk_gb}GB{mac_str}{ip_str}) [{status}]"
                        )
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ VM {vm.get('name', vm.get('vmid'))}: {e}")
            
            except Exception as e:
                logger.warning(f" ⚠️ QEmu Error: {e}")
            
            # ===== LXC Containers =====
            try:
                lxc_list = api.nodes(node_name).lxc.get()
            except Exception as e:
                logger.debug(f"No LXC containers: {e}")
                lxc_list = []
            
            if lxc_list:
                for ct in lxc_list:
                    vmid = ct['vmid']
                    try:
                        ct_config = api.nodes(node_name).lxc(vmid).config.get()
                        ct_name = ct_config.get('hostname', f"ct-{vmid}")
                        disk_gb = 0
                        
                        if 'rootfs' in ct_config:
                            disk_gb = extract_disk_size(ct_config['rootfs'])
                        
                        mac_addr = get_vm_mac(ct_config, 0)
                        ip_addr = get_ip_from_mac(mac_addr, arp_map) if mac_addr else None
                        status = 'active' if ct['status'] == 'running' else 'offline'
                        
                        ct_data = {
                            'name': ct_name,
                            'vmid': vmid,
                            'type': 'container',
                            'node': node_name,
                            'vcpus': ct_config.get('cores', 1),
                            'memory_mb': ct_config.get('memory', 512),
                            'disk_gb': disk_gb,
                            'mac_addr': mac_addr,
                            'ip_addr': ip_addr,
                            'status': status,
                            'description': f"Type: Container | VMID: {vmid} | Node: {node_name} | MAC: {mac_addr or 'N/A'}",
                        }
                        
                        vms.append(ct_data)
                        
                        mac_str = f" | MAC: {mac_addr}" if mac_addr else ""
                        ip_str = f" | IP: {ip_addr}" if ip_addr else ""
                        logger.info(
                            f" ✅ Ctr: {ct_name} "
                            f"({ct_data['vcpus']}C, {ct_data['memory_mb']}MB, {disk_gb}GB{mac_str}{ip_str}) [{status}]"
                        )
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ Container {vmid}: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return []
    
    logger.info(f"\n✅ Total: {len(vms)}\n")
    return vms


def get_or_create_cluster() -> Optional[int]:
    """Get or create cluster in NetBox"""
    r = session.get(
        f"{config['NB_URL']}/api/virtualization/clusters/?name={config['CLUSTER_NAME']}",
        headers={'Authorization': f"Token {config['NB_TOKEN']}"}
    )
    
    if r.status_code == 200 and r.json()['results']:
        cluster_id = r.json()['results'][0]['id']
        logger.info(f"✅ Cluster found (ID: {cluster_id})\n")
        return cluster_id
    
    logger.info("Creating cluster...")
    r = session.post(
        f"{config['NB_URL']}/api/virtualization/clusters/",
        json={'name': config['CLUSTER_NAME'], 'type': 'proxmox'},
        headers={'Authorization': f"Token {config['NB_TOKEN']}", 'Content-Type': 'application/json'}
    )
    
    if r.status_code in [200, 201]:
        cluster_id = r.json()['id']
        logger.info(f"✅ Cluster created (ID: {cluster_id})\n")
        return cluster_id
    
    logger.error(f"❌ Cluster error: {r.status_code}")
    return None


def integrate_port_scanning(vms: List[Dict]) -> bool:
    """✅ PORT SCANNING INTEGRATION"""
    if not config['PORT_SCANNING_ENABLED']:
        logger.info("Port scanning disabled in config\n")
        return True
    
    try:
        from port_scanning_integration import PortScanningIntegration
        import pynetbox
        
        logger.info("🔍 Port Scanning Integration Starting...\n")
        
        netbox_api = pynetbox.api(
            config['NB_URL'],
            token=config['NB_TOKEN']
        )
        
        ports = parse_ports_from_string(config['PORT_SCANNING_PORTS'])
        logger.info(f"Will scan {len(ports)} ports: {ports[:10]}...\n")
        
        scanner = PortScanningIntegration(
            netbox_api=netbox_api,
            netbox_url=config['NB_URL'],
            netbox_token=config['NB_TOKEN'],
            ssl_verify=config['NB_VERIFY_SSL'],
            timeout=config['PORT_SCANNING_TIMEOUT']
        )
        
        vms_to_scan = [vm for vm in vms if vm.get('ip_addr') and vm['status'] == 'active']
        logger.info(f"Scanning {len(vms_to_scan)} active VMs with IP addresses...\n")
        
        if vms_to_scan:
            successful = scanner.scan_all_vms_services(vms_to_scan, ports)
            logger.info(f"✅ Port scanning completed: {successful}/{len(vms_to_scan)} VMs scanned\n")
        else:
            logger.warning("No active VMs with IP addresses found for scanning\n")
        
        return True
    
    except ImportError:
        logger.warning("⚠️ Port scanning modules not found. Skipping.\n")
        return True
    except Exception as e:
        logger.error(f"❌ Port scanning failed: {e}\n")
        return False


def integrate_network_scanning(ports: List[int]) -> bool:
    """✅ NETWORK SCANNING INTEGRATION - Scan networks and create NetBox devices with duplicate prevention"""
    if not config['NETWORK_SCANNING_ENABLED']:
        logger.info("Network scanning disabled in config\n")
        return True
    
    if not config['NETWORK_SCANNING_NETWORKS']:
        logger.warning("⚠️ Network scanning enabled but no networks configured\n")
        return True
    
    try:
        from network_scanning_integration import NetworkScanningIntegration
        
        logger.info("🌐 Network Scanning Integration Starting...\n")
        logger.info("📌 Duplicate prevention enabled (check by device name & IP address)\n")
        
        networks = [n.strip() for n in config['NETWORK_SCANNING_NETWORKS'].split(',') if n.strip()]
        
        # Initialize with NetBox credentials for automatic device creation
        # NOTE: nb_discovered_hosts.py handles duplicate prevention automatically
        # - Checks by device name
        # - Checks by IP address in IPAM
        scanner = NetworkScanningIntegration(
            timeout=config['NETWORK_SCANNING_TIMEOUT'],
            max_threads=config['NETWORK_SCANNING_THREADS'],
            netbox_url=config['NB_URL'],
            netbox_token=config['NB_TOKEN']
        )
        
        # Scan networks AND create devices in NetBox automatically
        # Duplicate prevention: checks by device name and IP address
        created = scanner.scan_and_create_devices(networks, ports)
        
        logger.info(f"✅ Network scanning completed: {created} devices created/updated in NetBox\n")
        logger.info("✅ Duplicate prevention: No devices were duplicated (checked by name & IP)\n")
        
        return True
    
    except ImportError:
        logger.warning("⚠️ Network scanning modules not found. Skipping.\n")
        return True
    except Exception as e:
        logger.error(f"❌ Network scanning failed: {e}\n")
        return False


def main():
    """Main synchronization workflow"""
    
    logger.info("=" * 70)
    logger.info("NetBox Proxmox Sync - Infrastructure Synchronization v1.2.0")
    logger.info("=" * 70 + "\n")
    
    # Connect to Proxmox
    try:
        api = ProxmoxAPI(
            host=config['PVE_HOST'],
            user=config['PVE_USER'],
            token_name=config['PVE_TOKEN'],
            token_value=config['PVE_SECRET'],
            verify_ssl=config['PVE_VERIFY_SSL'],
        )
        logger.info(f"✅ Proxmox: {config['PVE_HOST']}\n")
    except Exception as e:
        logger.error(f"❌ Proxmox error: {e}")
        sys.exit(1)
    
    # Get VMs from Proxmox
    vms = get_proxmox_vms(api)
    
    if not vms:
        logger.error("❌ No VMs found")
        sys.exit(1)
    
    # Get or create cluster
    cluster_id = get_or_create_cluster()
    if not cluster_id:
        sys.exit(1)
    
    # Sync VMs to NetBox
    logger.info("Syncing VMs/Containers:")
    logger.info("-" * 70)
    
    synced = sum(
        1 for vm in vms
        if get_or_create_vm(
            session=session,
            nb_url=config["NB_URL"],
            nb_token=config["NB_TOKEN"],
            cluster_id=cluster_id,
            vm=vm,
        )
    )
    
    logger.info("-" * 70)
    logger.info(f"\n✅ {synced}/{len(vms)} VMs synchronized\n")
    
    # Parse ports for scanning features
    port_list = parse_ports_from_string(config['PORT_SCANNING_PORTS'])
    network_port_list = parse_ports_from_string(config['NETWORK_SCANNING_PORTS'])
    
    # Optional: Port scanning on known VMs
    integrate_port_scanning(vms)
    
    # Optional: Network scanning and discovery with NetBox device creation
    # ✅ Includes duplicate prevention (name & IP checks)
    integrate_network_scanning(network_port_list)
    
    logger.info("=" * 70)
    logger.info("✅ All synchronization tasks completed!")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
