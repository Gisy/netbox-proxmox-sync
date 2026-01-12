"""
NetBox VM Management - VMs/Container erstellen und aktualisieren
"""

import logging
from typing import Dict, Optional
import requests
from common import get_headers, make_api_request
from nb_interfaces import ensure_vm_interface_with_mac
from nb_ip import ensure_ip_on_interface_and_vm

logger = logging.getLogger(__name__)


def get_or_create_vm(
    session: requests.Session,
    nb_url: str,
    nb_token: str,
    cluster_id: int,
    vm: Dict,
    timeout: int = 10,
    retry_count: int = 3,
) -> bool:
    """Erstelle/Update VM oder Container in NetBox"""
    vm_name = vm["name"]
    headers = get_headers(nb_token)
    nb_url = nb_url.rstrip("/")
    
    response = make_api_request(
        session,
        "GET",
        f"{nb_url}/api/virtualization/virtual-machines/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        params={"name": vm_name, "cluster_id": cluster_id}
    )
    
    if not response or response.status_code != 200:
        logger.error(f"❌ {vm_name:30} Suche Fehler: {response.status_code if response else 'N/A'}")
        if response:
            logger.error(f"   Response: {response.text[:200]}")
        return False
    
    results = response.json().get("results", [])
    vm_exists = bool(results)
    
    if vm_exists:
        vm_id = results[0]["id"]
        logger.info(f" ✅ {vm_name:30} existiert (ID {vm_id})")
        
        update_data = {"status": vm["status"]}
        
        try:
            make_api_request(
                session,
                "PATCH",
                f"{nb_url}/api/virtualization/virtual-machines/{vm_id}/",
                headers,
                timeout=timeout,
                retry_count=retry_count,
                json=update_data
            )
        except Exception as e:
            logger.error(f"❌ {vm_name:30} Status-Update Fehler: {e}")
            return False
    else:
        payload = {
            "name": vm_name,
            "cluster": cluster_id,
            "status": vm["status"],
            "comments": vm.get("description", ""),
        }
        
        response = make_api_request(
            session,
            "POST",
            f"{nb_url}/api/virtualization/virtual-machines/",
            headers,
            timeout=timeout,
            retry_count=retry_count,
            json=payload
        )
        
        if not response or response.status_code not in (200, 201):
            logger.error(f"❌ {vm_name:30} create Fehler: {response.status_code if response else 'N/A'}")
            if response:
                logger.error(f"   Response: {response.text[:200]}")
            return False
        
        vm_id = response.json()["id"]
        logger.info(f" ✅ {vm_name:30} created (ID {vm_id})")
    
    update_data = {}
    
    if vm.get("vcpus"):
        update_data["vcpus"] = vm["vcpus"]
    
    if vm.get("memory_mb"):
        update_data["memory"] = vm["memory_mb"]
    
    if vm.get("disk_gb", 0) > 0:
        update_data["disk"] = vm["disk_gb"] * 1024
    
    if update_data:
        try:
            make_api_request(
                session,
                "PATCH",
                f"{nb_url}/api/virtualization/virtual-machines/{vm_id}/",
                headers,
                timeout=timeout,
                retry_count=retry_count,
                json=update_data
            )
        except Exception as e:
            logger.error(f"❌ {vm_name:30} Ressourcen-Update Fehler: {e}")
    
    iface_id = ensure_vm_interface_with_mac(
        session=session,
        nb_url=nb_url,
        nb_token=nb_token,
        vm_id=vm_id,
        eth_name="eth0",
        mac=vm.get("mac_addr"),
        timeout=timeout,
        retry_count=retry_count,
    )
    
    if iface_id and vm.get("ip_addr"):
        ensure_ip_on_interface_and_vm(
            session=session,
            nb_url=nb_url,
            nb_token=nb_token,
            vm_id=vm_id,
            iface_id=iface_id,
            ip_address=vm["ip_addr"],
            timeout=timeout,
            retry_count=retry_count,
        )
    
    return True


def get_or_create_cluster(
    session: requests.Session,
    nb_url: str,
    nb_token: str,
    cluster_name: str,
    timeout: int = 10,
    retry_count: int = 3,
) -> Optional[int]:
    """Hole oder erstelle Cluster in NetBox"""
    nb_url = nb_url.rstrip("/")
    headers = get_headers(nb_token)
    
    response = make_api_request(
        session,
        "GET",
        f"{nb_url}/api/virtualization/clusters/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        params={"name": cluster_name}
    )
    
    if response and response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            cluster_id = results[0]["id"]
            logger.info(f"✅ Cluster '{cluster_name}' gefunden (ID: {cluster_id})\n")
            return cluster_id
    
    logger.info(f"📝 Erstelle Cluster '{cluster_name}'...")
    
    payload = {
        "name": cluster_name,
        "type": "proxmox",
    }
    
    response = make_api_request(
        session,
        "POST",
        f"{nb_url}/api/virtualization/clusters/",
        headers,
        timeout=timeout,
        retry_count=retry_count,
        json=payload
    )
    
    if response and response.status_code in [200, 201]:
        cluster_id = response.json()["id"]
        logger.info(f"✅ Cluster '{cluster_name}' erstellt (ID: {cluster_id})\n")
        return cluster_id
    
    logger.error(f"❌ Cluster '{cluster_name}' erstellen fehlgeschlagen: {response.status_code if response else 'N/A'}")
    if response:
        logger.error(f"   Response: {response.text[:200]}")
    
    return None
