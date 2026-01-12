#!/usr/bin/env python3

"""
NetBox Device Management - Create and manage discovered hosts in NetBox

Handles automatic device creation for discovered network hosts with duplicate prevention
"""

import logging
from typing import Dict, Optional, List
import requests

logger = logging.getLogger(__name__)


class NetBoxDeviceManager:
    """Manage device creation and updates in NetBox for discovered hosts"""
    
    def __init__(self, netbox_url: str, netbox_token: str, ssl_verify: bool = True):
        """
        Initialize NetBox device manager
        
        Args:
            netbox_url: NetBox API URL (e.g., https://netbox.example.com)
            netbox_token: NetBox API token
            ssl_verify: Verify SSL certificates
        """
        self.netbox_url = netbox_url.rstrip('/')
        self.netbox_token = netbox_token
        self.ssl_verify = ssl_verify
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {netbox_token}',
            'Content-Type': 'application/json'
        })
        self.session.verify = ssl_verify
    
    def _get_device_by_ip(self, ip_address: str) -> Optional[int]:
        """
        Check if IP address is already assigned to any device
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Device ID if IP is already assigned, None otherwise
        """
        try:
            # Check IPAM for IP address
            url = f"{self.netbox_url}/api/ipam/ip-addresses/?address={ip_address}"
            r = self.session.get(url)
            
            if r.status_code == 200:
                results = r.json().get('results', [])
                if results:
                    ip_obj = results[0]
                    ip_id = ip_obj.get('id')
                    
                    # Check if IP is assigned to an interface
                    assigned_object_id = ip_obj.get('assigned_object_id')
                    assigned_object_type = ip_obj.get('assigned_object_type')
                    
                    if assigned_object_id and assigned_object_type == 'dcim.interface':
                        # Get interface and device
                        interface_url = f"{self.netbox_url}/api/dcim/interfaces/{assigned_object_id}/"
                        r_iface = self.session.get(interface_url)
                        
                        if r_iface.status_code == 200:
                            interface = r_iface.json()
                            device_id = interface.get('device', {}).get('id')
                            if device_id:
                                logger.debug(f"IP {ip_address} already assigned to device {device_id}")
                                return device_id
                    
                    # Also check if IP is directly assigned to device
                    assigned_object = ip_obj.get('assigned_object')
                    if assigned_object and 'device' in str(assigned_object_type).lower():
                        device_id = assigned_object.get('id')
                        if device_id:
                            return device_id
        
        except Exception as e:
            logger.debug(f"Error checking IP {ip_address}: {e}")
        
        return None
    
    def _get_existing_device(self, device_name: str, ip_address: str) -> Optional[int]:
        """
        Check if device already exists by name OR IP
        
        Args:
            device_name: Device name to check
            ip_address: IP address to check
            
        Returns:
            Device ID if exists, None otherwise
        """
        # Check 1: By device name
        try:
            url = f"{self.netbox_url}/api/dcim/devices/?name={device_name}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                device_id = r.json()['results'][0]['id']
                logger.info(f"📌 Device found by name: {device_name} (ID: {device_id})")
                return device_id
        except Exception as e:
            logger.debug(f"Error checking device by name: {e}")
        
        # Check 2: By IP address
        device_by_ip = self._get_device_by_ip(ip_address)
        if device_by_ip:
            logger.info(f"📌 Device found by IP: {ip_address} (ID: {device_by_ip})")
            return device_by_ip
        
        return None
    
    def get_or_create_site(self, site_name: str = 'Discovered') -> Optional[int]:
        """
        Get or create a site for discovered hosts
        
        Args:
            site_name: Site name
            
        Returns:
            Site ID or None
        """
        try:
            # Get existing site
            url = f"{self.netbox_url}/api/dcim/sites/?name={site_name}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                site_id = r.json()['results'][0]['id']
                logger.debug(f"Found existing site: {site_name} (ID: {site_id})")
                return site_id
            
            # Create new site
            logger.info(f"Creating site: {site_name}")
            url = f"{self.netbox_url}/api/dcim/sites/"
            data = {
                'name': site_name,
                'slug': site_name.lower().replace(' ', '-')
            }
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                site_id = r.json()['id']
                logger.info(f"✅ Site created: {site_name} (ID: {site_id})")
                return site_id
            else:
                logger.warning(f"Failed to create site: {r.status_code} {r.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error managing site: {e}")
            return None
    
    def get_or_create_device_type(self, type_name: str = 'Discovered-Host') -> Optional[int]:
        """
        Get or create a device type for discovered hosts
        
        Args:
            type_name: Device type name
            
        Returns:
            Device type ID or None
        """
        try:
            # Get existing device type
            url = f"{self.netbox_url}/api/dcim/device-types/?model={type_name}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                device_type_id = r.json()['results'][0]['id']
                logger.debug(f"Found existing device type: {type_name} (ID: {device_type_id})")
                return device_type_id
            
            # Get manufacturer for device type
            manufacturer_id = self._get_or_create_manufacturer('Generic')
            if not manufacturer_id:
                return None
            
            # Create new device type
            logger.info(f"Creating device type: {type_name}")
            url = f"{self.netbox_url}/api/dcim/device-types/"
            data = {
                'manufacturer': manufacturer_id,
                'model': type_name,
                'slug': type_name.lower().replace(' ', '-')
            }
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                device_type_id = r.json()['id']
                logger.info(f"✅ Device type created: {type_name} (ID: {device_type_id})")
                return device_type_id
            else:
                logger.warning(f"Failed to create device type: {r.status_code} {r.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error managing device type: {e}")
            return None
    
    def _get_or_create_manufacturer(self, manufacturer_name: str) -> Optional[int]:
        """Get or create a manufacturer"""
        try:
            # Get existing
            url = f"{self.netbox_url}/api/dcim/manufacturers/?name={manufacturer_name}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                return r.json()['results'][0]['id']
            
            # Create new
            url = f"{self.netbox_url}/api/dcim/manufacturers/"
            data = {
                'name': manufacturer_name,
                'slug': manufacturer_name.lower().replace(' ', '-')
            }
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                return r.json()['id']
            return None
        
        except Exception as e:
            logger.debug(f"Manufacturer error: {e}")
            return None
    
    def create_discovered_device(self, host_info: Dict, site_id: int, device_type_id: int) -> Optional[int]:
        """
        Create a device in NetBox for a discovered host
        Checks for duplicates by name and IP address
        
        Args:
            host_info: Host information from network scanner
                Expected keys: ip, name, open_ports, services
            site_id: NetBox site ID
            device_type_id: NetBox device type ID
            
        Returns:
            Device ID or None if failed
        """
        try:
            device_name = host_info.get('name', f"host-{host_info['ip'].replace('.', '-')}")
            ip_address = host_info['ip']
            open_ports = host_info.get('open_ports', [])
            services = host_info.get('services', [])
            
            # Check if device already exists (by name or IP)
            existing_device_id = self._get_existing_device(device_name, ip_address)
            if existing_device_id:
                logger.info(f"⏭️  Skipping existing device: {device_name} (ID: {existing_device_id})")
                return existing_device_id
            
            # Build device data
            service_list = [f"{svc[0]} ({svc[1]})" for svc in services]
            description = f"IP: {ip_address} | Open Ports: {open_ports} | Services: {', '.join(service_list)}"
            
            # Create device
            logger.info(f"➕ Creating new device: {device_name}")
            url = f"{self.netbox_url}/api/dcim/devices/"
            data = {
                'name': device_name,
                'device_type': device_type_id,
                'site': site_id,
                'status': 'active',
                'description': description,
            }
            
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                device_id = r.json()['id']
                logger.info(f"✅ Device created: {device_name} (ID: {device_id}) | IP: {ip_address}")
                return device_id
            else:
                logger.warning(f"Failed to create device: {r.status_code} {r.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating device: {e}")
            return None
    
    def create_device_interface(self, device_id: int, interface_name: str, ip_address: str) -> Optional[int]:
        """
        Create a network interface for a device (if not already present)
        
        Args:
            device_id: NetBox device ID
            interface_name: Interface name (e.g., 'eth0')
            ip_address: IP address
            
        Returns:
            Interface ID or None if failed
        """
        try:
            # Check if interface already exists for this device
            url = f"{self.netbox_url}/api/dcim/interfaces/?device_id={device_id}&name={interface_name}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                interface_id = r.json()['results'][0]['id']
                logger.info(f"📌 Interface already exists: {interface_name} (ID: {interface_id})")
                
                # Still assign IP if not already assigned
                self._assign_ip_to_interface(interface_id, ip_address)
                return interface_id
            
            # Create interface
            logger.info(f"➕ Creating interface {interface_name} for device {device_id}")
            url = f"{self.netbox_url}/api/dcim/interfaces/"
            data = {
                'device': device_id,
                'name': interface_name,
                'type': '1000base-t',  # Gigabit Ethernet
                'enabled': True
            }
            
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                interface_id = r.json()['id']
                logger.info(f"✅ Interface created: {interface_name} (ID: {interface_id})")
                
                # Assign IP to interface
                self._assign_ip_to_interface(interface_id, ip_address)
                return interface_id
            else:
                logger.warning(f"Failed to create interface: {r.status_code} {r.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating interface: {e}")
            return None
    
    def _assign_ip_to_interface(self, interface_id: int, ip_address: str) -> bool:
        """Assign IP address to interface (with duplicate prevention)"""
        try:
            # Check if IP already exists and is assigned to this interface
            url = f"{self.netbox_url}/api/ipam/ip-addresses/?address={ip_address}"
            r = self.session.get(url)
            
            if r.status_code == 200:
                results = r.json().get('results', [])
                if results:
                    ip_obj = results[0]
                    ip_id = ip_obj.get('id')
                    
                    # Check if already assigned to this interface
                    assigned_object_id = ip_obj.get('assigned_object_id')
                    if assigned_object_id == interface_id:
                        logger.info(f"📌 IP {ip_address} already assigned to interface {interface_id}")
                        return True
                    
                    # If assigned to different interface, update it
                    if assigned_object_id:
                        logger.info(f"⚠️  IP {ip_address} was assigned to interface {assigned_object_id}, updating...")
            else:
                # Create IP address
                url = f"{self.netbox_url}/api/ipam/ip-addresses/"
                data = {
                    'address': f"{ip_address}/32",  # Single host
                    'status': 'active'
                }
                r = self.session.post(url, json=data)
                
                if r.status_code not in [200, 201]:
                    logger.warning(f"Failed to create IP: {r.status_code}")
                    return False
                
                ip_id = r.json()['id']
                logger.info(f"✅ IP {ip_address} created (ID: {ip_id})")
            
            # Assign IP to interface
            url = f"{self.netbox_url}/api/dcim/interfaces/{interface_id}/"
            data = {'ip_addresses': [ip_id]}
            r = self.session.patch(url, json=data)
            
            if r.status_code in [200, 201]:
                logger.info(f"✅ IP {ip_address} assigned to interface {interface_id}")
                return True
            else:
                logger.warning(f"Failed to assign IP: {r.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error assigning IP: {e}")
            return False
    
    def create_device_service(self, device_id: int, port: int, service_name: str) -> Optional[int]:
        """
        Create a service for a device (open port) - with duplicate prevention
        
        Args:
            device_id: NetBox device ID
            port: Port number
            service_name: Service name (e.g., 'SSH', 'HTTP')
            
        Returns:
            Service ID or None if failed
        """
        try:
            service_identifier = f"{service_name}-{port}"
            
            # Check if service already exists
            url = f"{self.netbox_url}/api/dcim/services/?device_id={device_id}&name={service_identifier}"
            r = self.session.get(url)
            
            if r.status_code == 200 and r.json()['results']:
                service_id = r.json()['results'][0]['id']
                logger.debug(f"📌 Service already exists: {service_identifier} (ID: {service_id})")
                return service_id
            
            # Create new service
            logger.debug(f"Creating service {service_identifier} for device {device_id}")
            url = f"{self.netbox_url}/api/dcim/services/"
            data = {
                'device': device_id,
                'name': service_identifier,
                'ports': [port],
                'protocol': 'tcp'
            }
            
            r = self.session.post(url, json=data)
            
            if r.status_code in [200, 201]:
                service_id = r.json()['id']
                logger.debug(f"✅ Service created: {service_identifier} (ID: {service_id})")
                return service_id
            else:
                logger.debug(f"Service creation: {r.status_code}")
                return None
        
        except Exception as e:
            logger.debug(f"Service creation: {e}")
            return None
    
    def process_discovered_hosts(self, discovered_hosts: List[Dict], site_name: str = 'Discovered') -> int:
        """
        Process all discovered hosts and create/update devices in NetBox
        Prevents duplicate creation by checking IP and device name
        
        Args:
            discovered_hosts: List of discovered host dicts
            site_name: NetBox site name for discovered hosts
            
        Returns:
            Number of devices created/updated
        """
        logger.info(f"\n📍 Processing {len(discovered_hosts)} discovered hosts in NetBox...")
        logger.info(f"Checking for duplicates (by name and IP)...\n")
        
        # Get/create site and device type
        site_id = self.get_or_create_site(site_name)
        if not site_id:
            logger.error("Could not get/create site, aborting")
            return 0
        
        device_type_id = self.get_or_create_device_type('Discovered-Host')
        if not device_type_id:
            logger.error("Could not get/create device type, aborting")
            return 0
        
        # Process each host
        processed = 0
        for host_info in discovered_hosts:
            try:
                # Create device (checks for duplicates)
                device_id = self.create_discovered_device(host_info, site_id, device_type_id)
                
                if device_id:
                    # Create interface and assign IP
                    self.create_device_interface(device_id, 'eth0', host_info['ip'])
                    
                    # Create services for open ports
                    for service_name, protocol in host_info.get('services', []):
                        for port in host_info.get('open_ports', []):
                            self.create_device_service(device_id, port, service_name)
                    
                    processed += 1
                
            except Exception as e:
                logger.warning(f"Error processing host {host_info.get('ip')}: {e}")
        
        logger.info(f"✅ Processed {processed}/{len(discovered_hosts)} discovered hosts\n")
        return processed


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    manager = NetBoxDeviceManager(
        netbox_url='https://netbox.example.com',
        netbox_token='your_token'
    )
    
    # Example discovered hosts
    discovered_hosts = [
        {
            'ip': '192.168.1.100',
            'name': 'webserver-01',
            'open_ports': [22, 80, 443],
            'services': [('SSH', 'tcp'), ('HTTP', 'tcp'), ('HTTPS', 'tcp')]
        }
    ]
    
    manager.process_discovered_hosts(discovered_hosts)
