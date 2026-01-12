# NetBox Proxmox Sync v1.2.1 - Modular Command-Line Interface

## 🎯 Das Problem (Gelöst!)

**Vorher:** Alles läuft immer durch wenn du das Script aufrufst  
**Nachher:** Du kannst einzelne Module wählen! ✅

---

## ⚡ Quick Reference

```bash
# Alles ausführen
python netbox-sync.py

# Nur VMs synchronisieren
python netbox-sync.py vms

# Nur Port Scanning
python netbox-sync.py ports

# Nur Network Scanning
python netbox-sync.py network

# Hilfe anzeigen
python netbox-sync.py help
```

---

## 📋 Befehle im Detail

### 1. **all** (default)
Führt **alle Features** aus in dieser Reihenfolge:

```
python netbox-sync.py
```

**Schritte:**
1. ✅ Proxmox VMs/Container zur NetBox syncrounisieren
2. ✅ Port Scanning auf VMs (wenn enabled)
3. ✅ Network Scanning + Device Creation (wenn enabled)

**Nutze diese Version für:**
- Cron Jobs (stündlich, täglich, etc.)
- Komplette Infrastructure Synchronisation
- Standard Use Case

---

### 2. **vms**
Synchronisiert **nur Proxmox VMs/Container** zu NetBox

```bash
python netbox-sync.py vms
```

**Was passiert:**
- Verbindung zu Proxmox
- Alle VMs/Container werden gescannt
- MAC Adressen extrahiert
- OPNsense ARP Lookup (falls configured)
- Devices in NetBox erstellt/aktualisiert
- **Network Scanning NICHT ausgeführt**
- **Port Scanning NICHT ausgeführt**

**Nutze das wenn:**
- Du nur deine Proxmox Infrastruktur in NetBox haben willst
- Du Network Scanning später separat triggern möchtest
- Du Debugging für VM Sync brauchst

**Beispiel Output:**
```
$ python netbox-sync.py vms

======================================================================
NetBox Proxmox Sync - Infrastructure Synchronization v1.2.1
Mode: VMS
======================================================================

📌 Starting Proxmox VM/Container sync...

✅ Proxmox: pve.example.com

Scanning 2 nodes...

 Node: pve-node-1
 ✅ VM: webserver-01 (4C, 8192MB, 100GB | MAC: 02:00:00:00:00:01 | IP: 192.168.1.100) [active]
 ✅ VM: database-01 (8C, 16384MB, 500GB | MAC: 02:00:00:00:00:02 | IP: 192.168.1.50) [active]

✅ Total: 2

✅ Cluster found (ID: 5)

Syncing VMs/Containers:
======================================================================
✅ webserver-01 synced
✅ database-01 synced
======================================================================

✅ 2/2 VMs synchronized

======================================================================
✅ All vms synchronization tasks completed!
======================================================================
```

---

### 3. **ports**
Führt **nur Port Scanning** auf VMs durch

```bash
python netbox-sync.py ports
```

**Was passiert:**
- Verbindung zu Proxmox (um VMs zu finden)
- Port Scanning auf VMs mit IP-Adressen
- Gefundene Ports als Services in NetBox registriert
- **VM Sync NICHT ausgeführt (aber VMs werden gescannt)**
- **Network Scanning NICHT ausgeführt**

**Nutze das wenn:**
- VMs sind schon in NetBox (von früherem `python netbox-sync.py vms`)
- Du nur Services auf bekannten VMs aktualisieren willst
- Du Debugging für Port Scanning brauchst

**Beispiel Output:**
```
$ python netbox-sync.py ports

======================================================================
NetBox Proxmox Sync - Infrastructure Synchronization v1.2.1
Mode: PORTS
======================================================================

📌 Starting Port scanning...

✅ Proxmox: pve.example.com

Scanning 2 nodes...
[...]
✅ Total: 2

🔍 Port Scanning Integration Starting...

Will scan 3 ports: [22, 80, 443]...

Scanning 2 active VMs with IP addresses...

✅ webserver-01 (192.168.1.100):
  ✅ SSH-22 (OPEN)
  ✅ HTTP-80 (OPEN)
  ✅ HTTPS-443 (OPEN)

✅ database-01 (192.168.1.50):
  ✅ MySQL-3306 (OPEN)

✅ Port scanning completed: 2/2 VMs scanned

======================================================================
✅ All ports synchronization tasks completed!
======================================================================
```

---

### 4. **network**
Führt **nur Network Scanning** durch + Device Creation

```bash
python netbox-sync.py network
```

**Was passiert:**
- Scannt die in config.ini definierten Netzwerke
- Findet aktive Hosts (TCP Connectivity Check)
- Scannt Open Ports auf gefundenen Hosts
- **Erstellt Devices in NetBox automatisch** ✅
- **Duplikat-Vermeidung aktiv** (Check by name & IP)
- **Erstellt Interfaces und IP Adressen**
- **Erstellt Services pro Port**
- **VM Sync NICHT ausgeführt**
- **Port Scanning auf VMs NICHT ausgeführt**

**Nutze das wenn:**
- Du nur neue Hosts in deinem Netzwerk discovern willst
- Du separaten Schedule für Network Scanning haben willst
- Du Netzwerke scannen willst die NICHT in Proxmox sind
- Du Debugging für Network Scanning brauchst

**Beispiel Output:**
```
$ python netbox-sync.py network

======================================================================
NetBox Proxmox Sync - Infrastructure Synchronization v1.2.1
Mode: NETWORK
======================================================================

📌 Starting Network scanning...

🌐 Network Scanning Integration Starting...

📌 Duplicate prevention enabled (check by device name & IP address)

Processing 2 discovered hosts in NetBox...
Checking for duplicates (by name and IP)...

➕ Creating new device: webserver-01
✅ Device created: webserver-01 (ID: 123) | IP: 192.168.1.100
✅ Interface created: eth0 (ID: 456)
✅ IP 192.168.1.100 assigned to interface 456
✅ Service created: SSH-22 (ID: 789)
✅ Service created: HTTP-80 (ID: 790)
✅ Service created: HTTPS-443 (ID: 791)

📌 Device found by name: database-01 (ID: 124)
⏭️ Skipping existing device: database-01 (ID: 124)

✅ Processed 2/2 discovered hosts

✅ Network scanning completed: 1 devices created/updated in NetBox
✅ Duplicate prevention: No devices were duplicated (checked by name & IP)

======================================================================
✅ All network synchronization tasks completed!
======================================================================
```

---

## 🎯 Praktische Use Cases

### Use Case 1: Tägliche Synchronisation
```bash
# Alles synchronisieren (Default)
0 2 * * * cd /opt/netbox-proxmox-sync && python netbox-sync.py >> /var/log/netbox-sync.log 2>&1
```

### Use Case 2: Nur VMs, später Netzwerke
```bash
# VMs jede Stunde
0 * * * * cd /opt/netbox-proxmox-sync && python netbox-sync.py vms >> /var/log/netbox-sync-vms.log 2>&1

# Netzwerke nur nachts
0 3 * * * cd /opt/netbox-proxmox-sync && python netbox-sync.py network >> /var/log/netbox-sync-network.log 2>&1
```

### Use Case 3: VM Sync + Port Scanning, kein Network
```bash
# Nur VMs + Ports, keine externen Netzwerke
0 * * * * cd /opt/netbox-proxmox-sync && python netbox-sync.py vms && python netbox-sync.py ports >> /var/log/netbox-sync.log 2>&1
```

### Use Case 4: Nur Netzwerk-Discovery
```bash
# Externe Netzwerke, keine VMs
*/30 * * * * cd /opt/netbox-proxmox-sync && python netbox-sync.py network >> /var/log/netbox-sync-network.log 2>&1
```

### Use Case 5: Debugging
```bash
# VMs mit Debug Logging
python netbox-sync.py vms 2>&1 | tee debug.log

# Network Scanning mit Debug
python netbox-sync.py network 2>&1 | tee debug.log
```

---

## 🔧 Configuration

### Welche Features aktivieren?

In **config.ini**:

```ini
[port_scanning]
enabled = True                    # Aktiviert Port Scanning auf VMs
ports_to_scan = 22,80,443
timeout = 5
max_threads = 20

[network_scanning]
enabled = True                    # Aktiviert Network Scanning + Discovery
networks_to_scan = 192.168.1.0/24,10.0.0.0/16
ports_to_scan = 22,80,443,3306
timeout = 2
max_threads = 50
```

### Feature Matrix

| Command | VMs | Ports | Network |
|---------|-----|-------|---------|
| `all` | ✅ | ✅ | ✅ |
| `vms` | ✅ | ❌ | ❌ |
| `ports` | 🔍* | ✅ | ❌ |
| `network` | ❌ | ❌ | ✅ |

*`ports` scannt VMs um sie zu finden, aber synced sie nicht zu NetBox

---

## 📊 Logging & Debugging

### Logs anschauen (realtime)
```bash
# Alle logs
tail -f /var/log/netbox-sync.log

# Nur Errors
tail -f /var/log/netbox-sync.log | grep "ERROR\|❌"

# Nur Info
tail -f /var/log/netbox-sync.log | grep "✅"
```

### Debug Modus
```bash
# Mit vollständigem Debug Output
export LOG_LEVEL=DEBUG
python netbox-sync.py network
```

### Exit Codes
```bash
# Success (0)
python netbox-sync.py vms
echo $?  # 0

# Error (1)
python netbox-sync.py invalid-command
echo $?  # 1
```

---

## ⚡ Performance Tips

### Schnell die VMs synced?
```bash
python netbox-sync.py vms
# ~5-10 Sekunden (abhängig von Proxmox API)
```

### Schnell Networks scannen?
```bash
# Threads erhöhen in config.ini
[network_scanning]
max_threads = 100  # Default: 50

python netbox-sync.py network
# Mit 100 Threads: ~30 Sekunden für 254 Hosts
```

### Alles zusammen?
```bash
# All = VMs + Ports + Network
# ~2-3 Minuten je nach Größe
python netbox-sync.py
```

---

## 🆘 Fehlerbehandlung

### Problem: "No VMs found"
```bash
# Nur VMs anschauen
python netbox-sync.py vms

# Check Proxmox Verbindung in logs
# Check config.ini für PVE_HOST, Token etc.
```

### Problem: "Network scanning enabled but no networks configured"
```bash
# Edit config.ini
[network_scanning]
networks_to_scan = 192.168.1.0/24  # Add this!

# Try again
python netbox-sync.py network
```

### Problem: "Duplicate device created anyway"
```bash
# Das sollte NICHT passieren mit v1.2.1
# Aber wenn es passiert:

# Check logs für Duplicate Prevention
tail -f /var/log/netbox-sync.log | grep "Device found\|Skipping"

# Wenn Duplikat trotzdem da → Report!
```

---

## 📝 Git Deployment

```bash
# Update Hauptscript
cp netbox-sync_v1.2.1_MODULAR.py netbox-sync.py

# Commit
git add netbox-sync.py
git commit -m "v1.2.1: Modular command-line interface

- python netbox-sync.py all (default, alles)
- python netbox-sync.py vms (nur VMs)
- python netbox-sync.py ports (nur Ports)
- python netbox-sync.py network (nur Network)
- python netbox-sync.py help (hilfe)

Now you can run individual modules separately!"

git push origin main
```

---

## 🚀 Zusammenfassung

| Feature | Befehl |
|---------|--------|
| **Alles** | `python netbox-sync.py` |
| **Nur VMs** | `python netbox-sync.py vms` |
| **Nur Port Scan** | `python netbox-sync.py ports` |
| **Nur Network Scan** | `python netbox-sync.py network` |
| **Hilfe** | `python netbox-sync.py help` |

**v1.2.1 ist jetzt MODULAR und FLEXIBLE!** 🎉

Du kannst jetzt genau steuern was läuft - perfekt für verschiedene Schedules und Use Cases!
