"""
NetBox IP-Address Management - IPs synchronisieren und primary_ip4 setzen
"""

import logging
from typing import Optional
import requests
from common import get_headers, make_api_request

logger = logging.getLogger(__name__)


def validate_ip_address(ip_address: str) -> bool:
    """Validiere IP-Adresse Format"""
    import ipaddress
    try:
        ipaddress.ip_address(ip_address.split('/')[0])
        return True
    except ValueError:
        logger.warning(f"⚠️ Ungültiges IP-Format: {ip_address}")
        return False


def ensure_ip_on_interface_and_vm(
    session: requests.Session,
    nb_url: str,
    nb_token: str,
    vm_id: int,
    iface_id: int,
    ip_address: str,
    timeout: int = 10,
    retry_count: int = 3,
) -> Optional[int]:
    """Sorgt dafür, dass in NetBox eine IP-Address existiert und als primary_ip4 gesetzt ist"""
    if not ip_address:
        logger.debug("Kein IP-Address-String übergeben, überspringe.")
        return None
    
    if not validate_ip_address(ip_address):
        return None
    
    nb_url = nb_url.rstrip("/")
    headers = get_headers(nb_token)
    
    search_url = f"{nb_url}/api/ipam/ip-addresses/"
    
    response = make_api_request(
        session,
        "GET",
        search_url,
        headers,
        timeout=timeout,
        retry_count=retry_count,
        params={"q": ip_address}
    )
    
    if not response or response.status_code != 200:
        logger.error(f"❌ IP-Suche {ip_address} Fehler: {response.status_code if response else 'N/A'}")
        return None
    
    results = response.json().get("results", [])
    ip_obj = None
    
    for candidate in results:
        candidate_addr = candidate.get("address", "").split("/")[0]
        search_addr = ip_address.split("/")[0]
        if candidate_addr == search_addr:
            ip_obj = candidate
            break
    
    if ip_obj:
        ip_id = ip_obj["id"]
        logger.info(f" ↪ IP {ip_address} existiert bereits (ID {ip_id})")
    else:
        payload = {
            "address": ip_address,
        }
        
        response = make_api_request(
            session,
            "POST",
            search_url,
            headers,
            timeout=timeout,
            retry_count=retry_count,
            json=payload
        )
        
        if not response or response.status_code not in (200, 201):
            logger.error(f"❌ IP {ip_address} anlegen Fehler: {response.status_code if response else 'N/A'}")
            if response:
                logger.error(f"   Response: {response.text[:200]}")
            return None
        
        ip_obj = response.json()
        ip_id = ip_obj["id"]
        logger.info(f" ✅ IP {ip_address} angelegt (ID {ip_id})")
    
    try:
        needs_update = (
            ip_obj.get("assigned_object_type") != "virtualization.vminterface"
            or ip_obj.get("assigned_object_id") != iface_id
        )
        
        if needs_update:
            patch_payload = {
                "assigned_object_type": "virtualization.vminterface",
                "assigned_object_id": iface_id,
            }
            
            response = make_api_request(
                session,
                "PATCH",
                f"{nb_url}/api/ipam/ip-addresses/{ip_id}/",
                headers,
                timeout=timeout,
                retry_count=retry_count,
                json=patch_payload
            )
            
            if not response or response.status_code not in (200, 201):
                logger.error(f"❌ IP {ip_address} Interface-Zuordnung Fehler: {response.status_code if response else 'N/A'}")
                if response:
                    logger.error(f"   Response: {response.text[:200]}")
                return None
            
            logger.info(f" ✅ IP {ip_address} an vminterface ID {iface_id} gebunden")
        else:
            logger.info(f" ↪ IP {ip_address} ist bereits an vminterface ID {iface_id} gebunden")
    
    except Exception as e:
        logger.error(f"❌ IP {ip_address} Interface-Zuordnung Exception: {e}")
        return None
    
    try:
        vm_patch = {"primary_ip4": ip_id}
        
        response = make_api_request(
            session,
            "PATCH",
            f"{nb_url}/api/virtualization/virtual-machines/{vm_id}/",
            headers,
            timeout=timeout,
            retry_count=retry_count,
            json=vm_patch
        )
        
        if not response or response.status_code not in (200, 201):
            logger.error(f"❌ VM {vm_id} primary_ip4 setzen Fehler: {response.status_code if response else 'N/A'}")
            if response:
                logger.error(f"   Response: {response.text[:200]}")
            return None
        
        logger.info(f" ✅ VM ID {vm_id} primary_ip4 -> IP-ID {ip_id} ({ip_address})")
    
    except Exception as e:
        logger.error(f"❌ VM {vm_id} primary_ip4 setzen Exception: {e}")
        return None
    
    return ip_id
