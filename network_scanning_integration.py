#!/usr/bin/env python3

"""
Network Scanning Integration
Integrates network_scanner.py with netbox-sync.py workflow
"""

import logging
from typing import List, Dict
from network_scanner import NetworkScanner

logger = logging.getLogger(__name__)


class NetworkScanningIntegration:
    """Integrate network scanning into main sync workflow"""
    
    def __init__(self, timeout: int = 2, max_threads: int = 50):
        """
        Initialize network scanning integration
        
        Args:
            timeout: Socket timeout in seconds
            max_threads: Maximum parallel threads
        """
        self.scanner = NetworkScanner(timeout=timeout, max_threads=max_threads)
    
    def scan_networks(self, networks: List[str], ports: List[int]) -> List[Dict]:
        """
        Scan networks and return discovered hosts with open ports
        
        Args:
            networks: List of network strings (CIDR or IP ranges)
            ports: Ports to scan
            
        Returns:
            List of discovered hosts with open ports
        """
        logger.info("🔍 Network Scanning:")
        logger.info(f"Networks: {networks}")
        logger.info(f"Ports: {ports}\n")
        
        results = self.scanner.scan_networks(networks, ports)
        
        logger.info(f"\n✅ Network scanning completed!")
        logger.info(f"Found {len(results)} hosts with open ports\n")
        
        # Log results
        for host_info in results:
            logger.info(f"  • {host_info['ip']} ({host_info['name']})")
            logger.info(f"    Open ports: {host_info['open_ports']}")
            for service_info in host_info['services']:
                service_name, protocol = service_info
                logger.info(f"      - {service_name} ({protocol})")
        
        return results
    
    def scan_networks_for_netbox(self, networks: List[str], ports: List[int]) -> List[Dict]:
        """
        Scan networks and return data formatted for NetBox integration
        
        Args:
            networks: List of network strings
            ports: Ports to scan
            
        Returns:
            List of host dicts with NetBox-compatible format
        """
        results = self.scan_networks(networks, ports)
        
        # Convert to NetBox-compatible format
        netbox_results = []
        for host_info in results:
            netbox_item = {
                'name': host_info['name'],
                'ip': host_info['ip'],
                'type': 'discovered-host',  # Indicates discovered from network scan
                'open_ports': host_info['open_ports'],
                'services': host_info['services'],
            }
            netbox_results.append(netbox_item)
        
        return netbox_results


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    scanner = NetworkScanningIntegration(timeout=2, max_threads=50)
    
    # Example networks
    networks = ['192.168.1.0/24']
    ports = [22, 80, 443, 3306, 5432]
    
    results = scanner.scan_networks(networks, ports)
    print(f"\nDiscovered {len(results)} hosts")
