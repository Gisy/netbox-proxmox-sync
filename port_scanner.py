"""
Port Scanner - Scan open ports on VMs/Containers
"""

import logging
import socket
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


class PortScanner:
    """Scan ports on multiple hosts efficiently using threading"""
    
    def __init__(self, timeout: int = 5, max_threads: int = 20):
        """
        Initialize port scanner
        
        Args:
            timeout: Socket timeout in seconds
            max_threads: Maximum concurrent threads
        """
        self.timeout = timeout
        self.max_threads = max_threads
        self.lock = threading.Lock()
    
    def scan_port(self, host: str, port: int) -> bool:
        """
        Check if a single port is open
        
        Args:
            host: IP address or hostname
            port: Port number to check
            
        Returns:
            True if port is open, False otherwise
        """
        try:
            socket.setdefaulttimeout(self.timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except (socket.gaierror, socket.error) as e:
            logger.debug(f"Port scan error {host}:{port}: {e}")
            return False
    
    def scan_ports(self, host: str, ports: List[int]) -> Dict[int, bool]:
        """
        Scan multiple ports on a single host using threads
        
        Args:
            host: IP address or hostname
            ports: List of port numbers to scan
            
        Returns:
            Dictionary {port: is_open}
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(self.max_threads, len(ports))) as executor:
            futures = {
                executor.submit(self.scan_port, host, port): port 
                for port in ports
            }
            
            for future in as_completed(futures):
                port = futures[future]
                try:
                    is_open = future.result()
                    results[port] = is_open
                    
                    if is_open:
                        logger.info(f"  ✅ {host}:{port} OPEN")
                    else:
                        logger.debug(f"  ❌ {host}:{port} closed")
                except Exception as e:
                    logger.warning(f"  ⚠️ {host}:{port} error: {e}")
                    results[port] = False
        
        return results
    
    def scan_hosts(self, hosts: Dict[str, List[int]]) -> Dict[str, Dict[int, bool]]:
        """
        Scan multiple hosts in parallel
        
        Args:
            hosts: Dictionary {ip_address: [ports_to_scan]}
            
        Returns:
            Dictionary {ip_address: {port: is_open}}
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self.scan_ports, host, ports): host
                for host, ports in hosts.items()
            }
            
            for future in as_completed(futures):
                host = futures[future]
                try:
                    host_results = future.result()
                    results[host] = host_results
                except Exception as e:
                    logger.error(f"Scan failed for {host}: {e}")
                    results[host] = {}
        
        return results
    
    def get_open_ports(self, scan_results: Dict[int, bool]) -> List[int]:
        """
        Extract only open ports from scan results
        
        Args:
            scan_results: Dictionary from scan_ports()
            
        Returns:
            List of open port numbers
        """
        return [port for port, is_open in scan_results.items() if is_open]
    
    def get_common_service_ports(self) -> Dict[int, str]:
        """
        Get mapping of common ports to service names
        
        Returns:
            Dictionary {port: service_name}
        """
        return {
            22: "SSH",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            465: "SMTPS",
            587: "SMTP",
            636: "LDAPS",
            993: "IMAPS",
            995: "POP3S",
            1433: "MSSQL",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            5900: "VNC",
            6379: "Redis",
            8080: "HTTP-Proxy",
            8443: "HTTPS-Proxy",
            9200: "Elasticsearch",
            27017: "MongoDB",
            50070: "Hadoop",
        }
    
    def get_service_name(self, port: int) -> str:
        """
        Get service name for a port
        
        Args:
            port: Port number
            
        Returns:
            Service name or "Unknown"
        """
        services = self.get_common_service_ports()
        return services.get(port, f"Service-{port}")
