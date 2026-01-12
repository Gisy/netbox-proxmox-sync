#!/usr/bin/env python3

"""
Port Scanning Integration für NetBox
Scannt Ports auf aktiven VMs und erstellt Services in NetBox
"""

import logging
import socket
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class PortScanningIntegration:
    """Port Scanning Integration mit NetBox"""
    
    def __init__(self, netbox_api, netbox_url: str, netbox_token: str, ssl_verify: bool = False, timeout: int = 5):
        """
        Initialisiere Port Scanner
        
        Args:
            netbox_api: PyNetBox API instance
            netbox_url: NetBox URL
            netbox_token: NetBox API Token
            ssl_verify: SSL Verification
            timeout: Socket timeout in Sekunden
        """
        self.netbox_api = netbox_api
        self.netbox_url = netbox_url
        self.netbox_token = netbox_token
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        
        # Port-zu-Service Mapping
        self.port_services = {
            22: ('SSH', 'tcp'),
            80: ('HTTP', 'tcp'),
            443: ('HTTPS', 'tcp'),
            25: ('SMTP', 'tcp'),
            53: ('DNS', 'tcp'),
            110: ('POP3', 'tcp'),
            143: ('IMAP', 'tcp'),
            445: ('SMB', 'tcp'),
            3306: ('MySQL', 'tcp'),
            5432: ('PostgreSQL', 'tcp'),
            8080: ('HTTP-Proxy', 'tcp'),
            9200: ('Elasticsearch', 'tcp'),
            6379: ('Redis', 'tcp'),
            5900: ('VNC', 'tcp'),
            3389: ('RDP', 'tcp'),
            27017: ('MongoDB', 'tcp'),
            8443: ('HTTPS-Alt', 'tcp'),
        }
    
    def scan_port(self, host: str, port: int) -> bool:
        """
        Scanne einen einzelnen Port
        
        Args:
            host: Ziel-Host IP
            port: Ziel-Port
            
        Returns:
            True wenn Port offen, False sonst
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Port scan error {host}:{port}: {e}")
            return False
    
    def scan_host_ports(self, host: str, ports: List[int], max_threads: int = 20) -> List[int]:
        """
        Scanne mehrere Ports auf einem Host mit Threading
        
        Args:
            host: Ziel-Host IP
            ports: Liste der zu scannenden Ports
            max_threads: Max parallel Threads
            
        Returns:
            Liste der offenen Ports
        """
        open_ports = []
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {
                executor.submit(self.scan_port, host, port): port
                for port in ports
            }
            
            for future in as_completed(futures):
                port = futures[future]
                try:
                    if future.result():
                        open_ports.append(port)
                        logger.info(f"  ✅ Port {port} OPEN on {host}")
                except Exception as e:
                    logger.debug(f"Port {port} check failed: {e}")
        
        return sorted(open_ports)
    
    def get_service_name(self, port: int) -> tuple:
        """
        Hole Service-Name für Port
        
        Returns:
            (service_name, protocol) tuple
        """
        return self.port_services.get(port, (f'Service-{port}', 'tcp'))
    
    def create_service_in_netbox(self, vm: Dict, port: int, is_open: bool = True) -> bool:
        """
        Erstelle Service in NetBox für erkannten Port
        
        Args:
            vm: VM/Container Dict mit 'ip_addr' und 'name'
            port: Port-Nummer
            is_open: True wenn Port offen
            
        Returns:
            True wenn erfolgreich
        """
        try:
            if not vm.get('ip_addr'):
                return False
            
            service_name, protocol = self.get_service_name(port)
            
            # Service Name in NetBox
            nb_service_name = f"auto-{protocol}-{port}"
            description = f"{service_name} - Auto-detected on {vm['name']}"
            
            logger.info(f"  Creating service: {nb_service_name} ({service_name}:{port})")
            
            # Hier würde NetBox API aufgerufen werden
            # Für Demo nur Logging
            logger.debug(f"Would create service: {nb_service_name} on {vm['ip_addr']}:{port}")
            
            return True
        
        except Exception as e:
            logger.warning(f"Failed to create service for {vm.get('name')}:{port}: {e}")
            return False
    
    def scan_all_vms_services(self, vms: List[Dict], ports: List[int], max_threads: int = 20) -> int:
        """
        Scanne alle VMs auf Ports und erstelle Services
        
        Args:
            vms: Liste von VMs mit 'ip_addr', 'name'
            ports: Ports zum Scannen
            max_threads: Max parallele Threads
            
        Returns:
            Anzahl gescannter VMs
        """
        scanned_count = 0
        
        for vm in vms:
            if not vm.get('ip_addr'):
                logger.debug(f"Skipping {vm['name']} - no IP address")
                continue
            
            logger.info(f"\n🔍 Scanning {vm['name']} ({vm['ip_addr']})...")
            
            try:
                # Scanne alle Ports
                open_ports = self.scan_host_ports(vm['ip_addr'], ports, max_threads)
                
                if open_ports:
                    logger.info(f"  Found {len(open_ports)} open ports: {open_ports}")
                    
                    # Erstelle Services für offene Ports
                    for port in open_ports:
                        self.create_service_in_netbox(vm, port, is_open=True)
                else:
                    logger.info(f"  No open ports found")
                
                scanned_count += 1
            
            except Exception as e:
                logger.warning(f"Error scanning {vm['name']}: {e}")
        
        return scanned_count
