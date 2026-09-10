# Host Ethernet Sharing & Network Setup
 
Instructions and reference architecture for setting up a development laptop / ground station to provide Internet connection sharing and network routing to the ROV tether network (Raspberry Pi / BlueOS and NVIDIA Jetson).
 
---
 
## 1. Network Topology
 
The tethered ROV setup uses a `192.168.2.0/24` subnet:
 
```
                      ┌────────────────────────────────────────┐
                      │            Laptop / Host               │
                      │  IP: 192.168.2.1/24 (Tether/Ethernet)  │
                      │  Upstream WAN: WiFi / Cellular / LAN   │
                      └───────────┬────────────────┬───────────┘
                                  │ (Tether)       │
                                  │                │
            ┌─────────────────────┘                └─────────────────────┐
            ▼                                                            ▼
┌───────────────────────────────────────┐    ┌───────────────────────────────────────┐
│     BlueROV Raspberry Pi (BlueOS)     │    │      NVIDIA Jetson (Autonomy/ROS)     │
│ IP: 192.168.2.2/24                    │    │ IP: 192.168.2.11/24                   │
│ Gateway: 192.168.2.1                  │    │ Gateway: 192.168.2.1                  │
│ DNS: 8.8.8.8, 1.1.1.1, 192.168.2.1    │    │ DNS: 8.8.8.8, 1.1.1.1, 192.168.2.1    │
│ User: pi (pass: raspberry)            │    │ User: bluerov (pass: bluerov)         │
└───────────────────────────────────────┘    └───────────────────────────────────────┘
```
 
Both the Raspberry Pi and the NVIDIA Jetson expect the laptop to be present at `192.168.2.1` and to act as their default gateway and DNS forwarder/NAT router for outbound internet access (e.g. `apt update`, GitHub, time sync, pip packages).
 
---
 
## 2. Laptop Configuration (Linux / NetworkManager)
 
When setting up a new laptop running Linux with NetworkManager, follow these steps:
 
### Step 1: Identify your Ethernet interface
Plug in the Ethernet cable or USB-to-Ethernet adapter connected to the ROV tether switch:
```bash
nmcli device status
```
Identify the device name (e.g., `eth0`, `enp0s31f6`, or `enx00e08a365c33`).
 
### Step 2: Configure the connection profile for Internet sharing
Create or modify the Ethernet connection to use `ipv4.method shared` with static address `192.168.2.1/24`:
 
```bash
# List existing connection profiles
nmcli connection show
 
# Option A: Modify an existing wired connection profile (e.g. "Wired connection 1")
nmcli connection modify "Wired connection 1" \
    ipv4.method shared \
    ipv4.addresses 192.168.2.1/24 \
    connection.autoconnect yes
 
# Option B: Or create a dedicated connection profile bound to the interface
nmcli connection add type ethernet ifname <interface-name> con-name "ROV-Tether" \
    ipv4.method shared \
    ipv4.addresses 192.168.2.1/24 \
    connection.autoconnect yes
```
 
Apply and activate the connection:
```bash
nmcli connection up "ROV-Tether"  # or "Wired connection 1"
```
 
> **What `ipv4.method shared` does:**
> NetworkManager automatically configures IP forwarding in the kernel, adds iptables/nftables MASQUERADE/NAT rules to route traffic from the Ethernet subnet out through your active internet interface (WiFi/LAN), and starts a lightweight DNS forwarding daemon on `192.168.2.1`.
 
### Step 3: Enable kernel IP forwarding permanently
Ensure IP forwarding persists across system reboots:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-ip-forward.conf
sudo sysctl --system
```
 
### Step 4: Firewall configuration (if using UFW / iptables)
If `ufw` is active on the laptop, ensure routed packet forwarding is allowed:
```bash
sudo ufw default allow routed
sudo ufw reload
```
 
---
 
## 3. SSH Key Setup
 
Install your public SSH key onto both devices for passwordless access:
 
```bash
# Generate key if you haven't already
[ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -t ed25519
 
# Copy to Jetson (password: bluerov)
ssh-copy-id bluerov@192.168.2.11
 
# Copy to Raspberry Pi (password: raspberry)
ssh-copy-id pi@192.168.2.2
```
 
---
 
## 4. Verification Checklist
 
Run these tests from the laptop and inside each device:
 
### From Laptop:
```bash
ping -c 3 192.168.2.11  # Jetson reachable
ping -c 3 192.168.2.2   # Raspberry Pi reachable
```
 
### From Jetson (`ssh bluerov@192.168.2.11`):
```bash
ping -c 3 192.168.2.1              # Laptop gateway reachable
ping -c 3 8.8.8.8                  # Internet reachable
curl -I https://www.google.com     # DNS resolution and HTTPS egress functional
```
 
### From Raspberry Pi (`ssh pi@192.168.2.2`):
```bash
ping -c 3 192.168.2.1              # Laptop gateway reachable
ping -c 3 8.8.8.8                  # Internet reachable
curl -I https://www.google.com     # DNS resolution and HTTPS egress functional
```
 
---
 
## 5. Troubleshooting & Legacy Traps
 
* **Stale routes in `.bashrc`:** Ensure `~/.bashrc` on the Jetson does not contain scripts that delete `192.168.2.1` or re-add `192.168.2.2` as default gateway.
* **Conflicting NetworkManager profiles on Jetson:** Ensure only `enP8p1s0` is active and no legacy profiles (such as `Pi-Bridge`) attempt to override the default gateway.
* **BlueOS DHCP clashes:** BlueOS `cable-guy` (`/root/.config/blueos/cable-guy/settings-1.json`) is configured to treat `eth0` as `unmanaged` with static IP `192.168.2.2` so dynamic DHCP offers do not override the BlueOS static IP.
