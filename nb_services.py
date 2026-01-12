"""
NetBox Services Management - Create/update services for VMs in NetBox
"""

import logging
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class NetBoxServices:
    """Manage services/application ports in NetBox"""
    
    def __init__(self, base_url: str, api_token: str, ssl_verify: bool = True):
        """
        Initialize NetBox Services manager
        
        Args:
            base_url: NetBox URL (e.g., https://netbox.example.com)
            api_token: NetBox API token
            ssl_verify: Verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.ssl_verify = ssl_verify
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        })
    
    def get_service_url(self, ip_id: int) -> str:
        """Get API URL for services endpoint"""
        return f"{self.base_url}/api/ipam/services/?ip_address_id={ip_id}"
    
    def get_or_create_service(self, ip_id: int, port: int, protocol: str = "TCP", 
                             service_name: str = None) -> Optional[Dict]:
        """
        Get existing service or create new one
        
        Args:
            ip_id: NetBox IP address ID
            port: Port number
            protocol: "TCP" or "UDP"
            service_name: Service name (e.g., "SSH", "HTTP")
            
        Returns:
            Service object or None on error
        """
        if not service_name:
            from port_scanner import PortScanner
            scanner = PortScanner()
            service_name = scanner.get_service_name(port)
        
        try:
            # Check if service already exists
            url = self.get_service_url(ip_id)
            response = self.session.get(url, verify=self.ssl_verify)
            response.raise_for_status()
            
            existing = response.json().get('results', [])
            for service in existing:
                if service.get('ports') == [port] and service.get('protocol', '').upper() == protocol.upper():
                    logger.debug(f"Service already exists: {service_name}:{port}/{protocol}")
                    return service
            
            # Create new service
            return self._create_service(ip_id, port, protocol, service_name)
            
        except requests.RequestException as e:
            logger.error(f"Failed to get/create service: {e}")
            return None
    
    def _create_service(self, ip_id: int, port: int, protocol: str, 
                       service_name: str) -> Optional[Dict]:
        """
        Create a new service in NetBox
        
        Args:
            ip_id: NetBox IP address ID
            port: Port number
            protocol: "TCP" or "UDP"
            service_name: Service name
            
        Returns:
            Created service object or None on error
        """
        try:
            url = f"{self.base_url}/api/ipam/services/"
            
            data = {
                "name": f"auto-{protocol.lower()}-{port}",
                "ports": [port],
                "protocol": protocol.upper(),
                "description": f"{service_name} - Auto-detected"
            }
            
            # Note: You might need to link to the device instead
            # This depends on your NetBox version and setup
            # The service is created globally, not per IP
            
            response = self.session.post(url, json=data, verify=self.ssl_verify)
            response.raise_for_status()
            
            service = response.json()
            logger.info(f"✅ Created service: {service_name} ({protocol}/{port})")
            return service
            
        except requests.RequestException as e:
            logger.error(f"Failed to create service: {e}")
            return None
    
    def list_services_for_ip(self, ip_id: int) -> List[Dict]:
        """
        Get all services for an IP address
        
        Args:
            ip_id: NetBox IP address ID
            
        Returns:
            List of service objects
        """
        try:
            url = self.get_service_url(ip_id)
            response = self.session.get(url, verify=self.ssl_verify)
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.RequestException as e:
            logger.error(f"Failed to list services: {e}")
            return []
    
    def delete_service(self, service_id: int) -> bool:
        """
        Delete a service from NetBox
        
        Args:
            service_id: Service ID in NetBox
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.base_url}/api/ipam/services/{service_id}/"
            response = self.session.delete(url, verify=self.ssl_verify)
            response.raise_for_status()
            logger.info(f"✅ Deleted service ID {service_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to delete service: {e}")
            return False
    
    def sync_services(self, vm_name: str, ip_address: str, open_ports: List[int],
                     netbox_api) -> bool:
        """
        Synchronize scanned open ports with NetBox services
        
        Args:
            vm_name: VM name in NetBox
            ip_address: IP address to sync services for
            open_ports: List of open ports found
            netbox_api: NetBox API instance (from nb_ip.py)
            
        Returns:
            True if successful
        """
        try:
            # Get IP object from NetBox
            ip_obj = netbox_api.ipam.ip_addresses.get(address=ip_address)
            if not ip_obj:
                logger.warning(f"IP {ip_address} not found in NetBox")
                return False
            
            ip_id = ip_obj.id
            logger.info(f"Syncing services for {vm_name} ({ip_address})")
            
            # Create service for each open port
            from port_scanner import PortScanner
            scanner = PortScanner()
            
            created_count = 0
            for port in open_ports:
                service_name = scanner.get_service_name(port)
                if self.get_or_create_service(ip_id, port, "TCP", service_name):
                    created_count += 1
            
            logger.info(f"✅ Synced {created_count} services for {vm_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync services: {e}")
            return False
