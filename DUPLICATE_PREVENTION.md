# Duplicate Prevention in Network Scanning

## Das Problem

Wenn der Network Scanner mehrmals läuft, könnten Devices doppelt in NetBox erstellt werden:

```
❌ VORHER (Fehlerfall):
Lauf 1: 192.168.1.100 → Device "webserver-01" erstellt (ID: 123)
Lauf 2: 192.168.1.100 → Device "webserver-01" erstellt NOCHMAL (ID: 456) ❌ Duplikat!
Lauf 3: 192.168.1.100 → Device "webserver-01" erstellt NOCHMAL (ID: 789) ❌ Duplikat!
```

## Die Lösung

**Doppelte Überprüfung vor der Device-Erstellung:**

```
✅ NACHHER (mit Duplikat-Vermeidung):
Lauf 1: 192.168.1.100 → Device "webserver-01" erstellt (ID: 123)
Lauf 2: 192.168.1.100 → ✅ Gefunden! (ID: 123) → Skipped
Lauf 3: 192.168.1.100 → ✅ Gefunden! (ID: 123) → Skipped
```

---

## Implementierung

### 1️⃣ **Check by Device Name**

```python
def _get_existing_device(self, device_name: str, ip_address: str):
    # Check 1: By device name
    url = f"{self.netbox_url}/api/dcim/devices/?name={device_name}"
    r = self.session.get(url)
    
    if r.status_code == 200 and r.json()['results']:
        device_id = r.json()['results'][0]['id']
        logger.info(f"Device found by name: {device_name} (ID: {device_id})")
        return device_id
```

**Sucht:** `webserver-01` existent?
- ✅ JA → Return Device ID → Skip!
- ❌ NEIN → Check next

### 2️⃣ **Check by IP Address**

```python
def _get_device_by_ip(self, ip_address: str):
    # Check IPAM for IP address
    url = f"{self.netbox_url}/api/ipam/ip-addresses/?address={ip_address}"
    r = self.session.get(url)
    
    if r.status_code == 200:
        results = r.json().get('results', [])
        if results:
            ip_obj = results[0]
            assigned_object_id = ip_obj.get('assigned_object_id')
            
            # Get device from assigned interface
            interface_url = f"{self.netbox_url}/api/dcim/interfaces/{assigned_object_id}/"
            r_iface = self.session.get(interface_url)
            
            if r_iface.status_code == 200:
                interface = r_iface.json()
                device_id = interface.get('device', {}).get('id')
                if device_id:
                    return device_id
```

**Sucht:** IP `192.168.1.100` vorhanden?
- ✅ JA → Welches Device hat diese IP?
- ❌ NEIN → Create new

### 3️⃣ **Create Only If Not Found**

```python
def create_discovered_device(self, host_info):
    device_name = host_info.get('name', f"host-{ip}")
    ip_address = host_info['ip']
    
    # Check if device already exists (by name or IP)
    existing_device_id = self._get_existing_device(device_name, ip_address)
    if existing_device_id:
        logger.info(f"Skipping existing device: {device_name} (ID: {existing_device_id})")
        return existing_device_id
    
    # Only create if not found
    url = f"{self.netbox_url}/api/dcim/devices/"
    data = {
        'name': device_name,
        'device_type': device_type_id,
        'site': site_id,
        'status': 'active'
    }
    
    r = self.session.post(url, json=data)
    # ...
```

---

## Beispiel: Praktischer Ablauf

### Szenario 1: Erstes Mal ausgeführt

```
$ python netbox-sync.py

[INFO] Processing 2 discovered hosts in NetBox...
[INFO] Checking for duplicates (by name and IP)...

[INFO] ➕ Creating new device: webserver-01
[INFO] ✅ Device created: webserver-01 (ID: 123) | IP: 192.168.1.100
[INFO] ➕ Creating interface eth0 for device 123
[INFO] ✅ Interface created: eth0 (ID: 456)
[INFO] ✅ IP 192.168.1.100 assigned to interface 456

[INFO] ➕ Creating new device: database-01
[INFO] ✅ Device created: database-01 (ID: 124) | IP: 192.168.1.50
[INFO] ➕ Creating interface eth0 for device 124
[INFO] ✅ Interface created: eth0 (ID: 457)
[INFO] ✅ IP 192.168.1.50 assigned to interface 457

[INFO] ✅ Processed 2/2 discovered hosts
```

**Ergebnis:** 2 Devices erstellt ✅

### Szenario 2: Zweites Mal ausgeführt (gleiche Netzwerke)

```
$ python netbox-sync.py

[INFO] Processing 2 discovered hosts in NetBox...
[INFO] Checking for duplicates (by name and IP)...

[INFO] 📌 Device found by name: webserver-01 (ID: 123)
[INFO] ⏭️  Skipping existing device: webserver-01 (ID: 123)

[INFO] 📌 Device found by name: database-01 (ID: 124)
[INFO] ⏭️  Skipping existing device: database-01 (ID: 124)

[INFO] ✅ Processed 2/2 discovered hosts
```

**Ergebnis:** 0 neue Devices, 2 Devices gefunden und übersprungen ✅

### Szenario 3: Neue IP in bestehendem Netz

```
Neuer Host: 192.168.1.75 (monitoring-01)

$ python netbox-sync.py

[INFO] Processing 3 discovered hosts in NetBox...
[INFO] Checking for duplicates (by name and IP)...

[INFO] 📌 Device found by name: webserver-01 (ID: 123)
[INFO] ⏭️  Skipping existing device: webserver-01 (ID: 123)

[INFO] ➕ Creating new device: monitoring-01
[INFO] ✅ Device created: monitoring-01 (ID: 125) | IP: 192.168.1.75
[INFO] ➕ Creating interface eth0 for device 125
[INFO] ✅ Interface created: eth0 (ID: 458)
[INFO] ✅ IP 192.168.1.75 assigned to interface 458

[INFO] 📌 Device found by name: database-01 (ID: 124)
[INFO] ⏭️  Skipping existing device: database-01 (ID: 124)

[INFO] ✅ Processed 3/3 discovered hosts
```

**Ergebnis:** 1 neues Device, 2 bestehende übersprungen ✅

---

## Doppel-Check Logik

### Was wird überprüft?

| Check | Was | Beispiel |
|-------|-----|---------|
| **#1 Name** | Exakt gleicher Device-Name | `webserver-01` |
| **#2 IP** | IP in IPAM + zugewiesen zu Interface + Device | `192.168.1.100` |

### Reihenfolge

```
Host: webserver-01 / 192.168.1.100
  ↓
Check #1: Device mit Name "webserver-01"?
  ✅ FOUND → Return ID → Skip
  ❌ NOT FOUND ↓
Check #2: IP 192.168.1.100 in IPAM?
  ✅ FOUND → Return Device ID → Skip
  ❌ NOT FOUND ↓
CREATE new Device
```

---

## Interface & IP Duplikat-Vermeidung

### Interface Check

```python
def create_device_interface(self, device_id, interface_name, ip_address):
    # Check if interface already exists
    url = f"{self.netbox_url}/api/dcim/interfaces/?device_id={device_id}&name={interface_name}"
    r = self.session.get(url)
    
    if r.status_code == 200 and r.json()['results']:
        interface_id = r.json()['results'][0]['id']
        logger.info(f"Interface already exists: {interface_name} (ID: {interface_id})")
        self._assign_ip_to_interface(interface_id, ip_address)
        return interface_id
```

**Result:** Interfaces werden nicht doppelt erstellt ✅

### IP Assignment Check

```python
def _assign_ip_to_interface(self, interface_id, ip_address):
    # Check if IP already exists and is assigned
    url = f"{self.netbox_url}/api/ipam/ip-addresses/?address={ip_address}"
    r = self.session.get(url)
    
    if r.status_code == 200:
        results = r.json().get('results', [])
        if results:
            ip_obj = results[0]
            assigned_object_id = ip_obj.get('assigned_object_id')
            
            if assigned_object_id == interface_id:
                logger.info(f"IP {ip_address} already assigned to interface {interface_id}")
                return True
```

**Result:** IPs werden nicht doppelt zugewiesen ✅

### Service Check

```python
def create_device_service(self, device_id, port, service_name):
    service_identifier = f"{service_name}-{port}"
    
    # Check if service already exists
    url = f"{self.netbox_url}/api/dcim/services/?device_id={device_id}&name={service_identifier}"
    r = self.session.get(url)
    
    if r.status_code == 200 and r.json()['results']:
        service_id = r.json()['results'][0]['id']
        logger.debug(f"Service already exists: {service_identifier} (ID: {service_id})")
        return service_id
```

**Result:** Services werden nicht doppelt erstellt ✅

---

## Konsistenz-Prüfung

Was passiert wenn Device unterschiedliche IPs hat bei verschiedenen Läufen?

### Szenario: IP wechsel von 192.168.1.100 zu 192.168.1.101

```
Lauf 1:
- Device: webserver-01
- IP: 192.168.1.100 → erstellt

Lauf 2:
- Host: webserver-01
- IP: 192.168.1.101 (neue IP!)

Check:
  #1 Name "webserver-01" → FOUND (ID: 123) ✅
  ↓
  Return existing Device ID
  ↓
  Update IP in Interface
```

**Result:** Device wird NICHT neu erstellt, IP wird aktualisiert ✅

---

## Logging-Indikatoren

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Erfolgreich erstellt/aktualisiert |
| 📌 | Gefunden (existierend) |
| ⏭️  | Übersprungen (existierend) |
| ➕ | Neu erstellt |
| ❌ | Fehler |
| ⚠️ | Warnung |

---

## Best Practices

### 1. Regelmäßiges Ausführen (Safe)
```bash
# Cron Job - sicher, keine Duplikate
0 * * * * python /opt/netbox-proxmox-sync/netbox-sync.py
```

**Result:** Keine Duplikate, sogar bei mehrmaligem Lauf ✅

### 2. Mehrere Netzwerke Scannen (Safe)
```ini
[network_scanning]
networks_to_scan = 192.168.1.0/24,10.0.0.0/16,172.16.0.0/12
```

**Result:** Alle Hosts eindeutig registriert ✅

### 3. Ports anpassen (Safe)
```ini
ports_to_scan = 22,80,443  # Run 1
ports_to_scan = 22,80,443,3306,5432  # Run 2 (mehr Ports)
```

**Result:** Same Devices, Services updated ✅

---

## Fehlerbehandlung

### Case 1: API nicht erreichbar
```
[ERROR] Failed to create device: 503 Service Unavailable
[WARNING] Error processing host 192.168.1.100: Connection error
[INFO] Processed 1/3 discovered hosts (2 failed)
```

**Result:** Teilweise erfolgreich, Retry möglich ✅

### Case 2: Device Name Konflikt
```
Error: Device "webserver-01" exists aber mit unterschiedlichem Type
→ Check by IP
→ If IP different → Create new
→ If IP same → Return existing
```

**Result:** Intelligente Konfliktauflösung ✅

---

## Summary

✅ **Doppel-Check Logik:**
1. Nach Device-Name suchen
2. Nach IP-Adresse suchen
3. Nur erstellen wenn nicht gefunden

✅ **Interface & IP Safe:**
- Interfaces nicht doppelt
- IPs nicht doppelt zugewiesen
- Services eindeutig

✅ **Idempotent (idempotent):**
- Mehrmalige Ausführung möglich
- Keine Duplikate
- Automatische Updates

✅ **Production-Ready:**
- Error Handling
- Logging
- Graceful Degradation

**NetBox wird sauber gehalten - Keine Duplikate!** 🚀
