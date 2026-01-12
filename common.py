"""
Gemeinsame Utilities für NetBox Sync Scripts
"""

import logging
import sys
from typing import Dict, Optional
from pathlib import Path
import configparser
import requests

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


def load_config(config_file: Optional[str] = None) -> Dict:
    """Lade Konfiguration aus config.ini"""
    if config_file is None:
        config_file = Path(__file__).parent / 'config.ini'
    else:
        config_file = Path(config_file)
    
    if not config_file.exists():
        logger.error(f"❌ Config-Datei nicht gefunden: {config_file}")
        logger.info("Bitte kopiere config.ini.example nach config.ini und fülle die Werte aus")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except Exception as e:
        logger.error(f"❌ Config-Datei fehlerhaft: {e}")
        sys.exit(1)
    
    required_sections = {
        'proxmox': ['host', 'user', 'token', 'secret'],
        'netbox': ['url', 'token', 'cluster_name'],
    }
    
    for section, keys in required_sections.items():
        if not config.has_section(section):
            logger.error(f"❌ Section '[{section}]' fehlt in config.ini")
            sys.exit(1)
        
        for key in keys:
            if not config.has_option(section, key):
                logger.error(f"❌ Schlüssel '{key}' fehlt in Section '[{section}]'")
                sys.exit(1)
    
    return {
        'PVE_HOST': config.get('proxmox', 'host'),
        'PVE_USER': config.get('proxmox', 'user'),
        'PVE_TOKEN': config.get('proxmox', 'token'),
        'PVE_SECRET': config.get('proxmox', 'secret'),
        'NB_URL': config.get('netbox', 'url').rstrip('/'),
        'NB_TOKEN': config.get('netbox', 'token'),
        'CLUSTER_NAME': config.get('netbox', 'cluster_name'),
        'OPNSENSE_URL': config.get('opnsense', 'url', fallback='').rstrip('/') if config.has_section('opnsense') else '',
        'OPNSENSE_KEY': config.get('opnsense', 'key', fallback='') if config.has_section('opnsense') else '',
        'OPNSENSE_SECRET': config.get('opnsense', 'secret', fallback='') if config.has_section('opnsense') else '',
        'VERIFY_SSL': config.getboolean('general', 'verify_ssl', fallback=False),
        'REQUEST_TIMEOUT': config.getint('general', 'request_timeout', fallback=10),
        'RETRY_COUNT': config.getint('general', 'retry_count', fallback=3),
    }


def validate_config(config: Dict) -> bool:
    """Validiere alle Konfigurationswerte"""
    errors = []
    
    if not config['NB_URL'].startswith('http'):
        errors.append("❌ NB_URL muss mit http:// oder https:// beginnen")
    
    if len(config['NB_TOKEN']) < 20:
        errors.append("❌ NB_TOKEN scheint zu kurz zu sein")
    
    if not config['PVE_HOST']:
        errors.append("❌ PVE_HOST ist leer")
    
    if config['OPNSENSE_URL']:
        if not config['OPNSENSE_KEY'] or not config['OPNSENSE_SECRET']:
            errors.append("⚠️ OPNsense URL vorhanden aber Key/Secret fehlen - ARP-Lookup deaktiviert")
    
    if errors:
        for error in errors:
            logger.warning(error)
        return len([e for e in errors if e.startswith("❌")]) == 0
    
    return True


def get_session(verify_ssl: bool = False) -> requests.Session:
    """Erstelle eine Session mit optimalen Einstellungen"""
    session = requests.Session()
    session.verify = verify_ssl
    
    if not verify_ssl:
        requests.packages.urllib3.disable_warnings()
    
    return session


def get_headers(token: str) -> Dict[str, str]:
    """Erstelle Standard-API-Header"""
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def setup_logging(level: int = logging.INFO) -> None:
    """Konfiguriere Logging mit angenehmenem Format"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def make_api_request(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    timeout: int = 10,
    retry_count: int = 3,
    **kwargs
) -> Optional[requests.Response]:
    """Mache API-Request mit Retry-Logik"""
    method = method.upper()
    
    for attempt in range(1, retry_count + 1):
        try:
            response = session.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            return response
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout bei {method} {url} (Versuch {attempt}/{retry_count})")
            if attempt == retry_count:
                logger.error(f"❌ {method} {url} fehlgeschlagen nach {retry_count} Versuchen")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 Verbindungsfehler bei {method} {url}: {e} (Versuch {attempt}/{retry_count})")
            if attempt == retry_count:
                logger.error(f"❌ {method} {url} fehlgeschlagen - Verbindung unmöglich")
                return None
        except Exception as e:
            logger.error(f"❌ {method} {url} Fehler: {e}")
            return None
    
    return None
