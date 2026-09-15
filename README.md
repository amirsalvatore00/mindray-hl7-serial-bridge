\# Mindray BC-5150 HL7 to Virtual Serial Bridge



A production-grade Windows bridge that connects a \*\*Mindray BC-5150\*\* hematology analyzer (HL7 over TCP/IP) to any \*\*HIS/LIS\*\* system that only supports serial (COM) input — using `com0com` virtual serial ports.



Built for a real hospital deployment at \*\*Moheb Hospital\*\* (Tehran), after existing emulator tools kept losing configuration on every reboot.



\---



\## The Problem



Hospital lab analyzers like the \*\*Mindray BC-5150\*\* communicate results over \*\*HL7 v2.x\*\* using \*\*TCP/IP\*\*. But many legacy \*\*HIS/LIS\*\* systems only read results from a \*\*physical serial port (COM)\*\*.



Typical solutions used by labs:



\- Third-party serial-port emulators that \*\*lose IP/COM configuration on every reboot\*\*.

\- Tools that require the technician to \*\*re-enter IPs, ports, and COM settings manually\*\* every morning.

\- Bridges that \*\*crash\*\* when the analyzer is powered off or the network cable is unplugged.

\- Software that assumes the analyzer is a \*\*TCP client\*\*, but Mindray devices actually act as \*\*TCP servers\*\* — causing the infamous `Network connection error` on the device screen.



\### Additional constraints in our deployment



\- The PC has \*\*two NICs\*\*: one on the hospital LAN (`192.168.101.7`), one isolated to the analyzer (`192.168.200.192`).

\- The hospital uses \*\*Active Directory Group Policy\*\* that locks local firewall rules (`LocalFirewallRules: N/A (GPO-store only)`).

\- \*\*Kaspersky Endpoint Security\*\* with its own packet filter.

\- No Python runtime is installed on the clinical workstation — everything must ship as a \*\*single `.exe`\*\*.

\- The PC is \*\*rebooted nightly\*\*; all configuration must survive reboots with \*\*zero manual intervention\*\*.



\---



\## The Solution



A lightweight Python bridge compiled to a \*\*single-file Windows executable\*\* that:



1\. \*\*Auto-discovers\*\* the analyzer's TCP behavior:

&#x20;  - Scans a configurable list of ports (`5100, 5200, 5000, ...`).

&#x20;  - If an open port is found → bridges as \*\*Client\*\*.

&#x20;  - If no port is open → falls back to \*\*Server mode\*\* and waits for the analyzer to connect.



2\. \*\*Bridges TCP ↔ Virtual COM\*\* in both directions:

&#x20;  - TCP → COM: HL7 result messages from Mindray → COM10.

&#x20;  - COM → TCP: HL7 ACK from HIS on COM11 → back to Mindray.



3\. \*\*Survives everything\*\*:

&#x20;  - Auto-reconnect on cable unplug / analyzer reboot.

&#x20;  - Retries every 5 seconds forever — never crashes.

&#x20;  - Full logging to `server\_bridge\_log.txt`.



4\. \*\*Installs itself permanently\*\*:

&#x20;  - Static IP on the isolated NIC.

&#x20;  - Windows Firewall rule for inbound TCP 5200.

&#x20;  - Windows Task Scheduler entry (`onstart`, `SYSTEM`, `HIGHEST`) so it launches at boot \*\*before any user logs in\*\*.



5\. \*\*Never resets on reboot\*\* — unlike the commercial tools it replaces.



\---



\## Architecture


┌────────────────────┐ TCP/HL7 ┌──────────────────────────┐
│ Mindray BC-5150 │ ───────────────────► │ SmartMindrayBridge.exe │
│ 192.168.200.191 │ ◄─────────────────── │ 192.168.200.192 │
└────────────────────┘ HL7 ACK │ (isolated NIC) │
│ writes → COM10 │
└────────────┬─────────────┘
│
com0com pair
│
┌────────────▼─────────────┐
│ COM11 │
│ read by HIS / LIS │
└──────────────────────────┘

============================================================================




- **COM10** → written by the bridge, never opened by HIS.
- **COM11** → read by HIS, never opened by the bridge.

---

## Requirements

- **Windows 10 / 11** (or Windows Server 2019+)
- **Python 3.9+** on the build machine only
- **com0com** — https://sourceforge.net/projects/com0com/
- **Mindray BC-5150** configured for HL7 over TCP/IP

---

## Installation

### On the build machine

```bash
pip install pyinstaller pyserial
pyinstaller --noconsole --onefile SmartMindrayBridge.py


========================================================================================
