#!/usr/bin/env python3
"""
NetBox ↔ Proxmox Sync - Synchronize VMs and Containers with MAC-to-IP Matching

Features:
  - Synchronize VMs and containers from Proxmox to NetBox
  - Automatic MAC address mapping
  - IP addresses via OPNsense ARP lookup
  - Interface management (ethX, MAC, IP)
  - Status synchronization
  - Dry-run mode with ethX/MAC/IP mapping
  
Usage:
  ./netbox-sync.py              # Normal sync with ARP lookup
  ./netbox-sync.py --dry-run    # Only log, no changes
  ./netbox-sync.py --no-arp     # Without OPNsense ARP lookup
"""

import sys
import logging
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from common import (
    load_config,
    validate_config,
    get_session,
    get_headers,
    setup_logging,
    make_api_request,
    __version__,
)
from nb_vm import get_or_create_vm, get_or_create_cluster
from nb_interfaces import ensure_vm_interface_with_mac
from nb_ip import ensure_ip_on_interface_and_vm

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    print("❌ proxmoxer not installed. Install with: pip install -r requirements.txt")
    sys.exit(1)

logger = logging.getLogger(__name__)


class NetBoxProxmoxSync:
    """Main class for Proxmox → NetBox synchronization"""
    
    def __init__(self, config: Dict, dry_run: bool = False, use_arp: bool = True):
        """
        Initialize syncer
        
        Args:
            config: Configuration from load_config()
            dry_run: Only log, no changes
            use_arp: Enable OPNsense ARP lookup
        """
        self.config = config
        self.dry_run = dry_run
        self.use_arp = use_arp
        self.session = get_session(verify_ssl=config['VERIFY_SSL'])
        self.opn_session = None
        
        if self.use_arp and config['OPNSENSE_URL'] and config['OPNSENSE_KEY']:
            self.opn_session = get_session(verify_ssl=config['VERIFY_SSL'])
            self.opn_session.auth = (config['OPNSENSE_KEY'], config['OPNSENSE_SECRET'])
            logger.info("✅ OPNsense ARP lookup enabled\n")
        else:
            if self.use_arp:
                logger.warning("⚠️ OPNsense ARP lookup disabled (config incomplete)\n")
    
    def extract_disk_size(self, disk_str: str) -> int:
        """Extract disk size from disk string (in GB)"""
        try:
            if 'size=' in disk_str:
                size_part = disk_str.split('size=')[1].split(',')[0]
                if size_part.endswith('G'):
                    return int(size_part[:-1])
                elif size_part.endswith('M'):
                    return int(size_part[:-1]) // 1024
                elif size_part.endswith('T'):
                    return int(size_part[:-1]) * 1024
        except Exception as e:
            logger.debug(f"Disk parse error: {e}")
        
        return 0
    
    def get_vm_mac(self, vm_config: Dict, net_index: int) -> Optional[str]:
        """Get MAC address from VM/Container config for netX"""
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
        except Exception as e:
            logger.debug(f"MAC parse error: {e}")
        
        return None
    
    def fetch_arp_map(self) -> Dict[str, str]:
        """Fetch ARP table from OPNsense: MAC -> IP"""
        if not self.opn_session:
            return {}
        
        try:
            url = f"{self.config['OPNSENSE_URL']}/api/diagnostics/interface/get_arp"
            response = make_api_request(
                self.opn_session,
                "GET",
                url,
                {},
                timeout=self.config['REQUEST_TIMEOUT'],
                retry_count=self.config['RETRY_COUNT']
            )
            
            if not response or response.status_code != 200:
                logger.warning(f"⚠️ OPNsense ARP error: Status {response.status_code if response else 'N/A'}")
                return {}
            
            data = response.json()
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
            logger.warning(f"⚠️ OPNsense ARP error: {e}")
            return {}
    
    def get_ip_from_mac(self, mac: str, arp_map: Dict[str, str]) -> Optional[str]:
        """Find IP address for MAC address from ARP table"""
        if not mac or not arp_map:
            return None
        
        return arp_map.get(mac.lower())
    
    def log_eth_mapping(
        self,
        vm_name: str,
        vmid: int,
        is_container: bool,
        vm_config: Dict,
        arp_map: Dict[str, str]
    ) -> None:
        """Log netX -> ethX mapping with MAC + IP (dry-run)"""
        prefix = "Ctr" if is_container else "VM"
        
        for i in range(4):
            net_key = f'net{i}'
            if net_key not in vm_config:
                continue
            
            eth_name = f"eth{i}"
            mac = self.get_vm_mac(vm_config, i)
            ip = self.get_ip_from_mac(mac, arp_map) if mac else None
            
            logger.info(
                f"DRY-RUN: {prefix} {vm_name} (VMID {vmid}) "
                f"{net_key} → {eth_name} | MAC: {mac or 'N/A'} | IP: {ip or 'N/A'}"
            )
    
    def get_proxmox_vms(self, api) -> Tuple[List[Dict], Dict[str, str]]:
        """Get all VMs and containers from Proxmox"""
        arp_map = self.fetch_arp_map()
        vms: List[Dict] = []
        
        try:
            nodes = api.nodes.get()
            logger.info(f"Scanning {len(nodes)} nodes...\n")
            
            for node in nodes:
                node_name = node['node']
                logger.info(f" Node: {node_name}")
                
                try:
                    qemu = api.nodes(node_name).qemu.get()
                except Exception as e:
                    logger.debug(f"QEmu error: {e}")
                    qemu = []
                
                for vm in qemu:
                    try:
                        vm_config = api.nodes(node_name).qemu(vm['vmid']).config.get()
                        
                        disk_gb = 0
                        for disk_key in ['virtio0', 'scsi0', 'sata0', 'ide0', 'virtio1', 'scsi1']:
                            if disk_key in vm_config:
                                disk_gb = self.extract_disk_size(vm_config[disk_key])
                                if disk_gb > 0:
                                    break
                        
                        mac_addr = self.get_vm_mac(vm_config, 0)
                        ip_addr = self.get_ip_from_mac(mac_addr, arp_map) if mac_addr else None
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
                        
                        self.log_eth_mapping(vm['name'], vm['vmid'], False, vm_config, arp_map)
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ VM {vm.get('name', vm.get('vmid'))}: {e}")
                
                try:
                    lxc_list = api.nodes(node_name).lxc.get()
                except Exception as e:
                    logger.debug(f"No LXC: {e}")
                    lxc_list = []
                
                for ct in lxc_list:
                    vmid = ct['vmid']
                    try:
                        ct_config = api.nodes(node_name).lxc(vmid).config.get()
                        ct_name = ct_config.get('hostname', f"ct-{vmid}")
                        
                        disk_gb = 0
                        if 'rootfs' in ct_config:
                            disk_gb = self.extract_disk_size(ct_config['rootfs'])
                        
                        mac_addr = self.get_vm_mac(ct_config, 0)
                        ip_addr = self.get_ip_from_mac(mac_addr, arp_map) if mac_addr else None
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
                        
                        self.log_eth_mapping(ct_name, vmid, True, ct_config, arp_map)
                    
                    except Exception as e:
                        logger.warning(f" ⚠️ Container {vmid}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Proxmox error: {e}")
            return [], arp_map
        
        logger.info(f"\n✅ Total: {len(vms)} VMs/containers found\n")
        return vms, arp_map
    
    def sync(self) -> bool:
        """Perform synchronization"""
        logger.info("=" * 70)
        logger.info(f"Proxmox → NetBox Sync v{__version__}")
        if self.dry_run:
            logger.info("🧪 DRY-RUN MODE (no changes)")
        logger.info("=" * 70 + "\n")
        
        try:
            api = ProxmoxAPI(
                host=self.config['PVE_HOST'],
                user=self.config['PVE_USER'],
                token_name=self.config['PVE_TOKEN'],
                token_value=self.config['PVE_SECRET'],
                verify_ssl=self.config['VERIFY_SSL'],
            )
            logger.info(f"✅ Proxmox: {self.config['PVE_HOST']}\n")
        except Exception as e:
            logger.error(f"❌ Proxmox connection error: {e}")
            return False
        
        vms, arp_map = self.get_proxmox_vms(api)
        
        if not vms:
            logger.error("❌ No VMs/containers found")
            return False
        
        if self.dry_run:
            logger.info("\n🧪 DRY-RUN: Exiting without NetBox changes\n")
            return True
        
        cluster_id = get_or_create_cluster(
            session=self.session,
            nb_url=self.config['NB_URL'],
            nb_token=self.config['NB_TOKEN'],
            cluster_name=self.config['CLUSTER_NAME'],
            timeout=self.config['REQUEST_TIMEOUT'],
            retry_count=self.config['RETRY_COUNT'],
        )
        
        if not cluster_id:
            logger.error("❌ Cluster could not be found/created")
            return False
        
        logger.info("Synchronizing VMs/containers with NetBox:")
        logger.info("-" * 70)
        
        synced = sum(
            1 for vm in vms
            if get_or_create_vm(
                session=self.session,
                nb_url=self.config['NB_URL'],
                nb_token=self.config['NB_TOKEN'],
                cluster_id=cluster_id,
                vm=vm,
                timeout=self.config['REQUEST_TIMEOUT'],
                retry_count=self.config['RETRY_COUNT'],
            )
        )
        
        logger.info("-" * 70)
        logger.info(f"\n✅ {synced}/{len(vms)} VMs/containers synchronized\n")
        
        if arp_map and self.opn_session:
            logger.info(f"📊 ARP entries found: {len(arp_map)}\n")
        
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Synchronize Proxmox VMs to NetBox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--dry-run', action='store_true', help='Only log, no changes')
    parser.add_argument('--no-arp', action='store_true', help='Disable OPNsense ARP lookup')
    parser.add_argument('--config', type=str, help='Config file path (default: config.ini)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    
    config = load_config(args.config)
    
    if not validate_config(config):
        logger.error("❌ Configuration invalid - please check the values")
        sys.exit(1)
    
    syncer = NetBoxProxmoxSync(
        config=config,
        dry_run=args.dry_run,
        use_arp=not args.no_arp
    )
    
    success = syncer.sync()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
