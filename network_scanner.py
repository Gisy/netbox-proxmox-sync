#!/usr/bin/env python3

"""
Network Scanner - Network discovery and host detection
Scans IP networks and discovers active hosts
"""

import logging
import socket
import ipaddress
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class NetworkScanner:
    """Scan networks for active hosts"""
    
    def __init__(self, timeout: int = 2, max_threads: int = 50):
        """
        Initialize network scanner
        
        Args:
            timeout: Connection timeout in seconds
            max_threads: Maximum concurrent threads for scanning
        """
        self.timeout = timeout
        self.max_threads = max_threads
        self.active_hosts: Set[str] = set()
    
    def ping_host(self, ip: str) -> bool:
        """
        Check if host is reachable via socket connection
        
        Args:
            ip: IP address to check
            
        Returns:
            True if host responds, False otherwise
        """
        try:
            # Try to connect on port 22 (SSH) as indicator of active host
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 22))
            sock.close()
            
            if result == 0:
                return True
            
            # If port 22 closed, try port 80 (HTTP)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            if result == 0:
                return True
            
            # Try port 443 (HTTPS)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 443))
            sock.close()
            
            return result == 0
        
        except Exception as e:
            logger.debug(f"Ping {ip}: {e}")
            return False
    
    def scan_network(self, network: str) -> List[str]:
        """
        Scan a network and return list of active hosts
        
        Args:
            network: Network in CIDR notation (e.g., '192.168.1.0/24')
            
        Returns:
            List of active IP addresses
        """
        try:
            # Parse network
            net = ipaddress.ip_network(network, strict=False)
            hosts = list(net.hosts())
            
            logger.info(f"Scanning {len(hosts)} hosts in {network}...")
            
            active_hosts = []
            
            # Use thread pool for parallel scanning
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                # Submit all ping tasks
                futures = {
                    executor.submit(self.ping_host, str(ip)): str(ip)
                    for ip in hosts
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    ip = futures[future]
                    try:
                        if future.result():
                            active_hosts.append(ip)
                            logger.debug(f"✅ Host active: {ip}")
                    except Exception as e:
                        logger.debug(f"Error scanning {ip}: {e}")
                    
                    # Progress indicator
                    if completed % 10 == 0:
                        logger.debug(f"Progress: {completed}/{len(hosts)}")
            
            logger.info(f"Found {len(active_hosts)} active hosts in {network}\n")
            return active_hosts
        
        except ValueError as e:
            logger.error(f"Invalid network {network}: {e}")
            return []
        except Exception as e:
            logger.error(f"Network scan error: {e}")
            return []
    
    def scan_networks(self, networks: List[str]) -> Dict[str, List[str]]:
        """
        Scan multiple networks
        
        Args:
            networks: List of networks in CIDR notation
            
        Returns:
            Dictionary mapping network to list of active hosts
        """
        results = {}
        
        for network in networks:
            logger.info(f"Starting scan for network: {network}")
            results[network] = self.scan_network(network)
        
        return results
    
    def scan_and_get_ports(self, ip: str, ports: List[int]) -> Dict[int, bool]:
        """
        Scan specific ports on a host
        
        Args:
            ip: IP address to scan
            ports: List of ports to check
            
        Returns:
            Dictionary mapping port to open status
        """
        port_status = {}
        
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                port_status[port] = (result == 0)
            except Exception as e:
                logger.debug(f"Port {port} scan error on {ip}: {e}")
                port_status[port] = False
        
        return port_status
