"""
Port Scanning Integration - Scan VMs and sync services with NetBox
"""

import logging
from typing import List, Dict, Optional
from port_scanner import PortScanner
from nb_services import NetBoxServices

logger = logging.getLogger(__name__)


class PortScanningIntegration:
    """Integrate port scanning with NetBox synchronization"""
    
    def __init__(self, netbox_api, netbox_url: str, netbox_token: str, 
                 ssl_verify: bool = True, timeout: int = 5):
        """
        Initialize port scanning integration
        
        Args:
            netbox_api: NetBox API instance (from pynetbox)
            netbox_url: NetBox URL
            netbox_token: NetBox API token
            ssl_verify: Verify SSL certificates
            timeout: Socket timeout for port scanning
        """
        self.netbox_api = netbox_api
        self.scanner = PortScanner(timeout=timeout, max_threads=20)
        self.services = NetBoxServices(netbox_url, netbox_token, ssl_verify)
        self.logger = logging.getLogger(__name__)
    
    def get_ports_from_config(self, config: Dict) -> List[int]:
        """
        Get ports to scan from config file
        
        Args:
            config: Configuration dictionary with 'port_scanning' section
            
        Returns:
            List of port numbers
        """
        try:
            ports_str = config.get('port_scanning', {}).get('ports_to_scan', '')
            
            if not ports_str:
                # Default common ports
                return [22, 80, 443, 3306, 5432, 8080, 8443]
            
            ports = []
            for part in ports_str.split(','):
                part = part.strip()
                if '-' in part:
                    # Range like "1-100"
                    start, end = part.split('-')
                    ports.extend(range(int(start), int(end) + 1))
                else:
                    # Single port
                    ports.append(int(part))
            
            return sorted(list(set(ports)))
        except Exception as e:
            self.logger.warning(f"Failed to parse ports from config: {e}")
            return [22, 80, 443]
    
    def scan_vm(self, vm_name: str, ip_address: str, ports: List[int]) -> Dict[int, bool]:
        """
        Scan a single VM for open ports
        
        Args:
            vm_name: VM name
            ip_address: IP address to scan
            ports: List of ports to scan
            
        Returns:
            Dictionary {port: is_open}
        """
        self.logger.info(f"🔍 Scanning {vm_name} ({ip_address}) for {len(ports)} ports...")
        results = self.scanner.scan_ports(ip_address, ports)
        
        open_ports = [p for p, is_open in results.items() if is_open]
        self.logger.info(f"  Found {len(open_ports)} open ports: {open_ports}")
        
        return results
    
    def scan_all_vms(self, vms: List[Dict], ports: List[int]) -> Dict[str, Dict[int, bool]]:
        """
        Scan multiple VMs in parallel
        
        Args:
            vms: List of VM dictionaries {name, ip_address}
            ports: List of ports to scan
            
        Returns:
            Dictionary {vm_name: {port: is_open}}
        """
        self.logger.info(f"🔍 Scanning {len(vms)} VMs for ports...")
        
        hosts = {vm['ip_address']: ports for vm in vms if 'ip_address' in vm}
        results = self.scanner.scan_hosts(hosts)
        
        self.logger.info(f"✅ Port scanning completed for {len(results)} hosts")
        return results
    
    def sync_vm_services(self, vm_name: str, ip_address: str, ports: List[int]) -> bool:
        """
        Scan VM and sync services with NetBox
        
        Args:
            vm_name: VM name
            ip_address: IP address
            ports: List of ports to scan
            
        Returns:
            True if successful
        """
        # Scan ports
        scan_results = self.scan_vm(vm_name, ip_address, ports)
        open_ports = [p for p, is_open in scan_results.items() if is_open]
        
        if not open_ports:
            self.logger.warning(f"  No open ports found for {vm_name}")
            return True
        
        # Sync with NetBox
        return self.services.sync_services(vm_name, ip_address, open_ports, self.netbox_api)
    
    def sync_all_vms_services(self, vms: List[Dict], ports: List[int]) -> int:
        """
        Scan all VMs and sync services with NetBox
        
        Args:
            vms: List of VM dictionaries {name, ip_address}
            ports: List of ports to scan
            
        Returns:
            Number of successfully synced VMs
        """
        self.logger.info(f"🔍 Scanning and syncing {len(vms)} VMs...")
        
        successful = 0
        for vm in vms:
            try:
                if self.sync_vm_services(vm['name'], vm['ip_address'], ports):
                    successful += 1
            except Exception as e:
                self.logger.error(f"Failed to sync {vm['name']}: {e}")
        
        self.logger.info(f"✅ Synced {successful}/{len(vms)} VMs")
        return successful


def integrate_port_scanning(config, netbox_api, common_logger=None) -> bool:
    """
    Main integration function for port scanning
    
    Args:
        config: Configuration dictionary
        netbox_api: NetBox API instance
        common_logger: Optional logger instance
        
    Returns:
        True if successful
    """
    if common_logger:
        logger = common_logger
    
    try:
        # Check if port scanning is enabled
        if not config.get('port_scanning', {}).get('enabled', False):
            logger.info("Port scanning is disabled in config")
            return True
        
        # Get configuration
        netbox_url = config['netbox']['url']
        netbox_token = config['netbox']['token']
        ssl_verify = config['netbox'].get('ssl_verify', True)
        timeout = config.get('port_scanning', {}).get('timeout', 5)
        
        # Initialize integration
        integration = PortScanningIntegration(
            netbox_api=netbox_api,
            netbox_url=netbox_url,
            netbox_token=netbox_token,
            ssl_verify=ssl_verify,
            timeout=timeout
        )
        
        # Get ports to scan
        ports = integration.get_ports_from_config(config)
        logger.info(f"Will scan ports: {ports}")
        
        # Get all VMs from NetBox and scan them
        devices = netbox_api.dcim.devices.filter(
            has_interfaces=True,
            site=config['proxmox'].get('netbox_site', '')
        )
        
        vms = []
        for device in devices:
            # Get primary IP
            if hasattr(device, 'primary_ip') and device.primary_ip:
                vms.append({
                    'name': device.name,
                    'ip_address': str(device.primary_ip.address.split('/')[0])
                })
        
        if vms:
            integration.sync_all_vms_services(vms, ports)
        else:
            logger.warning("No VMs found with IP addresses")
        
        return True
        
    except Exception as e:
        logger.error(f"Port scanning integration failed: {e}")
        return False
