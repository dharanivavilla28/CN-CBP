"""
Mininet Custom Topology for Emergency Communication Network
Part of: ML-Enhanced SDN Emergency Communication Network

Run on an SDN/Mininet Linux VM or environment:
    sudo mn --custom mininet/topology.py --topo emergency_topo --controller=remote,ip=127.0.0.1,port=6633 --switch ovs,protocols=OpenFlow13

NOTE: Mininet is a Linux-only package. On Windows/macOS this file can be
imported and syntax-checked safely; the stubs below replace every mininet
symbol so no NameError is raised outside a real Mininet environment.
"""
import sys as _sys

try:
    from mininet.topo import Topo                          # type: ignore[import]
    from mininet.net import Mininet                        # type: ignore[import]
    from mininet.node import RemoteController, OVSSwitch   # type: ignore[import]
    from mininet.cli import CLI                            # type: ignore[import]
    from mininet.log import setLogLevel, info              # type: ignore[import]
    from mininet.link import TCLink                        # type: ignore[import]
    _MININET_AVAILABLE = True
except ImportError:
    # ── Stubs so the module is importable on Windows / non-Mininet hosts ── #
    _MININET_AVAILABLE = False

    class Topo:  # type: ignore[no-redef]
        """Stub Topo base class."""
        def __init__(self, **opts): pass
        def addHost(self, name, **opts): return name
        def addSwitch(self, name, **opts): return name
        def addLink(self, node1, node2, **opts): pass

    class Mininet:  # type: ignore[no-redef]
        """Stub Mininet runner."""
        def __init__(self, **kwargs): pass
        def start(self): pass
        def stop(self): pass
        def pingAll(self): pass

    class RemoteController:  # type: ignore[no-redef]
        """Stub RemoteController."""
        def __init__(self, name, **kwargs): pass

    class OVSSwitch:  # type: ignore[no-redef]
        """Stub OVSSwitch."""
        pass

    class CLI:  # type: ignore[no-redef]
        """Stub CLI."""
        def __init__(self, net): pass

    class TCLink:  # type: ignore[no-redef]
        """Stub TCLink."""
        pass

    def setLogLevel(level: str) -> None:  # type: ignore[no-redef]
        pass

    def info(msg: str) -> None:  # type: ignore[no-redef]
        _sys.stdout.write(msg)


class EmergencyCampusTopo(Topo):
    """
    Emergency Communication Network Topology:
      Hosts:
        - Security      (10.0.0.1) -> s1
        - Medical       (10.0.0.2) -> s2
        - Admin         (10.0.0.3) -> s4
        - MainGate      (10.0.0.4) -> s3
        - BackGate      (10.0.0.5) -> s4
        - ControlRoom   (10.0.0.6) -> s1
      Switches:
        - s1, s2, s3, s4
      Trunk mesh links with configurable bandwidth/delay/loss.
    """

    def build(self):
        # 1. Add OpenFlow switches
        s1 = self.addSwitch("s1", dpid="0000000000000001", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", dpid="0000000000000002", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", dpid="0000000000000003", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", dpid="0000000000000004", protocols="OpenFlow13")

        # 2. Add Emergency Hosts with specific IPs and MACs
        h_security = self.addHost("h_sec", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h_medical  = self.addHost("h_med", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        h_admin    = self.addHost("h_adm", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
        h_maingate = self.addHost("h_mg",  ip="10.0.0.4/24", mac="00:00:00:00:00:04")
        h_backgate = self.addHost("h_bg",  ip="10.0.0.5/24", mac="00:00:00:00:00:05")
        h_control  = self.addHost("h_ctrl", ip="10.0.0.6/24", mac="00:00:00:00:00:06")

        # 3. Host-to-Switch Access Links
        self.addLink(h_security, s1, bw=100, delay="2ms", loss=0)
        self.addLink(h_control,  s1, bw=1000, delay="1ms", loss=0)
        self.addLink(h_medical,  s2, bw=100, delay="2.5ms", loss=0)
        self.addLink(h_maingate, s3, bw=100, delay="4ms", loss=0)
        self.addLink(h_admin,    s4, bw=100, delay="3ms", loss=0)
        self.addLink(h_backgate, s4, bw=100, delay="4.5ms", loss=0)

        # 4. Inter-Switch Backbone Trunk Links
        self.addLink(s1, s2, bw=1000, delay="8ms",  loss=0.1)
        self.addLink(s1, s3, bw=1000, delay="9.5ms", loss=0.1)
        self.addLink(s2, s4, bw=1000, delay="11ms", loss=0.2)
        self.addLink(s3, s4, bw=1000, delay="8.5ms", loss=0.1)
        self.addLink(s2, s3, bw=500,  delay="14ms", loss=0.3)


topos = {"emergency_topo": (lambda: EmergencyCampusTopo())}


def run_network():
    """Direct runner script for Mininet CLI.

    Must be run as root on a Linux host with Mininet installed:
        sudo python mininet/topology.py
    """
    if not _MININET_AVAILABLE:
        raise RuntimeError(
            "Mininet is not installed. This script must be run on a Linux host "
            "with Mininet installed (e.g. inside a Mininet VM).\n"
            "Install: https://mininet.org/download/"
        )
    topo = EmergencyCampusTopo()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6633),
        link=TCLink,
        autoSetMacs=True,
    )
    info("*** Starting Emergency SDN Network...\n")
    net.start()
    info("*** Testing network reachability (pingall)...\n")
    net.pingAll()
    info("*** Running Mininet CLI. Type 'exit' to terminate.\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_network()
