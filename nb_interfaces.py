"""
NetBox VM Interface Management - MAC-Adressen synchronisieren
"""

import logging
from typing import Optional
import requests
from common import get_headers, make_api_request

logger = logging.getLogger(__name__)


def ensure_vm_interface_with_mac(
    session: requests.Session,
    nb_url: str,
    nb_token: str,
    vm_id: int,
    eth_name: str,
    mac: Optional[str],
    timeout: int = 10,
    retry_count: int = 3,
) -> Optional[int]:
    """
    Sorgt dafür, dass an der NetBox-VM ein Interface existiert,
    die MAC als primary_mac_address gesetzt ist und gibt die Interface-ID zurück.
    """
    if not mac:
        logger.info(f" ↪ kein MAC für {eth_name}, überspringe Interface-Sync")
        return None
    
    nb_url = nb_url.rstrip("/")
    headers = get_headers(nb_token)
    
    response = make_api_request(
        session,
        "GET",
        f"{nb_url}/api/virtualization/interfaces/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        params={"virtual_machine_id": vm_id, "name": eth_name}
    )
    
    if not response or response.status_code != 200:
        logger.warning(f" ⚠️ IF-GET {eth_name} an VM {vm_id} fehlgeschlagen: {response.status_code if response else 'N/A'}")
        return None
    
    data = response.json()
    
    if data.get("count", 0) > 0:
        iface = data["results"][0]
        iface_id = iface["id"]
        logger.info(f" ↪ Interface {eth_name} an VM {vm_id} existiert (ID {iface_id})")
    else:
        payload = {
            "virtual_machine": vm_id,
            "name": eth_name,
            "description": f"MAC: {mac}",
        }
        
        response = make_api_request(
            session,
            "POST",
            f"{nb_url}/api/virtualization/interfaces/",
            headers,
            timeout=timeout,
            retry_count=retry_count,
            json=payload
        )
        
        if not response or response.status_code not in (200, 201):
            logger.warning(f" ⚠️ IF-POST {eth_name} an VM {vm_id} fehlgeschlagen: {response.status_code if response else 'N/A'}")
            return None
        
        iface = response.json()
        iface_id = iface["id"]
        logger.info(f" ✅ Interface {eth_name} an VM {vm_id} angelegt (ID {iface_id})")
    
    response = make_api_request(
        session,
        "GET",
        f"{nb_url}/api/dcim/mac-addresses/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        params={
            "mac_address": mac,
            "assigned_object_type": "virtualization.vminterface",
            "assigned_object_id": iface_id,
        }
    )
    
    if not response or response.status_code != 200:
        logger.warning(f" ⚠️ MAC-GET {mac} an IF {iface_id} fehlgeschlagen: {response.status_code if response else 'N/A'}")
        return iface_id
    
    data = response.json()
    
    if data.get("count", 0) > 0:
        mac_obj = data["results"][0]
        mac_id = mac_obj["id"]
        logger.info(f" ↪ MAC {mac} für IF {iface_id} existiert (ID {mac_id})")
    else:
        payload = {
            "mac_address": mac,
            "assigned_object_type": "virtualization.vminterface",
            "assigned_object_id": iface_id,
        }
        
        response = make_api_request(
            session,
            "POST",
            f"{nb_url}/api/dcim/mac-addresses/",
            headers,
            timeout=timeout,
            retry_count=retry_count,
            json=payload
        )
        
        if not response or response.status_code not in (200, 201):
            logger.warning(f" ⚠️ MAC-POST {mac} an IF {iface_id} fehlgeschlagen: {response.status_code if response else 'N/A'}")
            return iface_id
        
        mac_obj = response.json()
        mac_id = mac_obj["id"]
        logger.info(f" ✅ MAC {mac} an IF {iface_id} angelegt (ID {mac_id})")
    
    response = make_api_request(
        session,
        "GET",
        f"{nb_url}/api/virtualization/interfaces/{iface_id}/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
    )
    
    if not response or response.status_code != 200:
        logger.warning(f" ⚠️ IF-GET {iface_id} für primary_mac_address fehlgeschlagen: {response.status_code if response else 'N/A'}")
        return iface_id
    
    iface = response.json()
    current = iface.get("primary_mac_address")
    
    if isinstance(current, dict) and current.get("id") == mac_id:
        logger.info(f" ↪ primary_mac_address an IF {iface_id} ist bereits {mac}")
        return iface_id
    
    patch_payload = {"primary_mac_address": mac_id}
    
    response = make_api_request(
        session,
        "PATCH",
        f"{nb_url}/api/virtualization/interfaces/{iface_id}/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        json=patch_payload
    )
    
    if not response or response.status_code not in (200, 202):
        logger.warning(f" ⚠️ primary_mac_address-SET an IF {iface_id} fehlgeschlagen: {response.status_code if response else 'N/A'}")
        return iface_id
    
    logger.info(f" ✅ primary_mac_address {mac} an IF {iface_id} gesetzt")
    return iface_id
