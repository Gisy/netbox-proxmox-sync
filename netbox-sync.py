#!/usr/bin/env python3

"""
NetBox ↔ Proxmox Sync - mit MAC-to-IP Matching über OPNsense ARP + Port Scanning

Synchronisiert VMs und Container mit Status + IPs via DHCP/ARP-Lookup
+ Optional: Port Scanning und Service-Erstellung in NetBox
+ Dry-Run ethX/MAC/IP-Mapping
"""

import sys
import logging
import configparser
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from nb_interfaces import ensure_vm_interface_with_mac
from nb_ip import ensure_ip_on_interface_and_vm
from nb_vm import get_or_create_vm
import requests
from proxmoxer import ProxmoxAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DRY_RUN = True  # aktuell NUR Logging der Zuordnung, keine NetBox-Änderungen


def load_config() -> Dict:
    """Lade Konfiguration aus config.ini"""
    config_file = Path(__file__).parent / 'config.ini'
    if not config_file.exists():
        logger.error(f"Config nicht gefunden: {config_file}")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    return {
        'PVE_HOST': config.get('proxmox', 'host'),
        'PVE_USER': config.get('proxmox', 'user'),
        'PVE_TOKEN': config.get('proxmox', 'token'),
        'PVE_SECRET': config.get('proxmox', 'secret'),
        'NB_URL': config.get('netbox', 'url'),
        'NB_TOKEN': config.get('netbox', 'token'),
        'CLUSTER_NAME': config.get('netbox', 'cluster_name'),
        'OPNSENSE_URL': config.get('opnsense', 'url', fallback=''),
        'OPNSENSE_KEY': config.get('opnsense', 'key', fallback=''),
        'OPNSENSE_SECRET': config.get('opnsense', 'secret', fallback=''),
        # Port Scanning (NEW)
        'PORT_SCANNING_ENABLED': config.getboolean('port_scanning', 'enabled', fallback=False),
        'PORT_SCANNING_PORTS': config.get('port_scanning', 'ports_to_scan', fallback='22,80,443'),
        'PORT_SCANNING_TIMEOUT': config.getint('port_scanning', 'timeout', fallback=5),
        'PORT_SCANNING_THREADS': config.getint('port_scanning', 'max_threads', fallback=20),
    }


config = load_config()

requests.packages.urllib3.disable_warnings()
session = requests.Session()
session.verify = False

# OPNsense Session falls vorhanden
opn_session = None
if config['OPNSENSE_URL'] and config['OPNSENSE_KEY']:
    opn_session = requests.Session()
    opn_session.auth = (config['OPNSENSE_KEY'], config['OPNSENSE_SECRET'])
    opn_session.verify = False
    logger.info("✅ OPNsense ARP-Lookup aktiviert\n")


def extract_disk_size(disk_str: str) -> int:
    """Extrahiere Festplattengröße aus Disk-String"""
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
    """Hole MAC-Adresse aus VM/Container Config für netX"""
    try:
        net_key = f'net{net_index}'
        if net_key not in vm_config:
            return None
        
        net_str = vm_config[net_key]
        # Format: virtio=MAC,... oder e1000=MAC,...
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
    """Hole ARP-Tabelle von OPNsense: MAC -> IP"""
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
        
        logger.debug(f"OPNsense ARP: {len(arp_map)} Einträge")
        return arp_map
    except Exception as e:
        logger.warning(f"⚠️ OPNsense ARP Error: {e}")
        return {}


def get_ip_from_mac(mac: str, arp_map: Dict[str, str]) -> Optional[str]:
    """Finde IP-Adresse für MAC-Adresse aus ARP-Tabelle"""
    if not mac or not arp_map:
        return None
    
    mac_lower = mac.lower()
    return arp_map.get(mac_lower)


def log_eth_mapping(vm_name: str, vmid: int, is_container: bool, vm_config: Dict, arp_map: Dict[str, str]) -> None:
    """
    Dry-Run: logge netX -> ethX Mapping mit MAC + IP
    Legt noch nichts in NetBox an.
    """
    prefix = "Ctr" if is_container else "VM"
    for i in range(4):  # net0..net3 → eth0..eth3
        net_key = f'net{i}'
        if net_key not in vm_config:
            continue
        
        eth_name = f"eth{i}"
        mac = get_vm_mac(vm_config, i)
        ip = get_ip_from_mac(mac, arp_map) if mac else None
        
        logger.info(
            f"DRY-RUN: {prefix} {vm_name} (VMID {vmid}) "
            f"{net_key} → {eth_name} | MAC: {mac or 'N/A'} | IP: {ip or 'N/A'}"
        )


def get_proxmox_vms(api) -> Tuple[List[Dict], Dict[str, str]]:
    """Hole alle VMs und Container aus Proxmox mit Status und MACs + Dry-Run ethX-Mapping"""
    arp_map = fetch_arp_map()
    vms: List[Dict] = []
    
    try:
        nodes = api.nodes.get()
        logger.info(f"Scanne {len(nodes)} Nodes...\n")
        
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
                        
                        # Haupt-MAC für Übersicht (net0)
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
                        
                        # Dry-Run ethX/MAC/IP Mapping loggen
                        log_eth_mapping(vm['name'], vm['vmid'], False, vm_config, arp_map)
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ VM {vm.get('name', vm.get('vmid'))}: {e}")
            
            except Exception as e:
                logger.warning(f" ⚠️ QEmu Error: {e}")
            
            # ===== LXC Container =====
            try:
                lxc_list = api.nodes(node_name).lxc.get()
            except Exception as e:
                logger.debug(f"No LXC: {e}")
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
                        
                        # Dry-Run ethX/MAC/IP Mapping loggen
                        log_eth_mapping(ct_name, vmid, True, ct_config, arp_map)
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ Container {vmid}: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return [], arp_map
    
    logger.info(f"\n✅ Total: {len(vms)}\n")
    return vms, arp_map


def get_or_create_cluster() -> Optional[int]:
    """Hole oder erstelle Cluster"""
    r = session.get(
        f"{config['NB_URL']}/api/virtualization/clusters/?name={config['CLUSTER_NAME']}",
        headers={'Authorization': f"Token {config['NB_TOKEN']}"}
    )
    
    if r.status_code == 200 and r.json()['results']:
        cluster_id = r.json()['results'][0]['id']
        logger.info(f"✅ Cluster (ID: {cluster_id})\n")
        return cluster_id
    
    logger.info("Create cluster...")
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


def parse_ports_from_config(ports_str: str) -> List[int]:
    """
    Parse port string from config
    Supports: 22,80,443 or 1-1000,3000-3100 or mixed
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
        return [22, 80, 443]  # Default


def integrate_port_scanning(vms: List[Dict]) -> bool:
    """
    ✅ PORT SCANNING INTEGRATION (NEW)
    Scan ports on all VMs and create services in NetBox
    """
    if not config['PORT_SCANNING_ENABLED']:
        logger.info("Port scanning disabled in config\n")
        return True
    
    try:
        from port_scanning_integration import PortScanningIntegration
        import pynetbox
        
        logger.info("🔍 Port Scanning Integration Starting...\n")
        
        # Initialize NetBox API
        netbox_api = pynetbox.api(
            config['NB_URL'],
            token=config['NB_TOKEN']
        )
        
        # Parse ports from config
        ports = parse_ports_from_config(config['PORT_SCANNING_PORTS'])
        logger.info(f"Will scan {len(ports)} ports: {ports[:10]}...\n")
        
        # Initialize scanner
        scanner = PortScanningIntegration(
            netbox_api=netbox_api,
            netbox_url=config['NB_URL'],
            netbox_token=config['NB_TOKEN'],
            ssl_verify=False,
            timeout=config['PORT_SCANNING_TIMEOUT']
        )
        
        # Scan all VMs with IP addresses
        vms_to_scan = [
            vm for vm in vms 
            if vm.get('ip_addr') and vm['status'] == 'active'
        ]
        
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


def main():
    logger.info("=" * 70)
    logger.info("Proxmox → NetBox Sync (mit MAC-to-IP via OPNsense ARP + Port Scanning)")
    logger.info("=" * 70 + "\n")
    
    try:
        api = ProxmoxAPI(
            host=config['PVE_HOST'],
            user=config['PVE_USER'],
            token_name=config['PVE_TOKEN'],
            token_value=config['PVE_SECRET'],
            verify_ssl=False,
        )
        logger.info(f"✅ Proxmox: {config['PVE_HOST']}\n")
    except Exception as e:
        logger.error(f"❌ Proxmox error: {e}")
        sys.exit(1)
    
    vms, arp_map = get_proxmox_vms(api)
    
    if not vms:
        logger.error("❌ No VMs found")
        sys.exit(1)
    
    cluster_id = get_or_create_cluster()
    if not cluster_id:
        sys.exit(1)
    
    logger.info("Sync (nur VMs, kein Interface/IP-Link, DRY-RUN für ethX):")
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
    logger.info(f"\n✅ {synced}/{len(vms)} synchronized\n")
    
    if arp_map:
        logger.info(f"📊 ARP-Einträge gefunden: {len(arp_map)}\n")
    
    # ✅ PORT SCANNING INTEGRATION (NEW)
    logger.info("=" * 70)
    logger.info("Starting Port Scanning Integration...")
    logger.info("=" * 70 + "\n")
    
    integrate_port_scanning(vms)
    
    logger.info("=" * 70)
    logger.info("✅ All synchronization tasks completed!")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
