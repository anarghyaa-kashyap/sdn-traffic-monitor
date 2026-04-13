# =============================================================================
# topology.py
# Custom Mininet topology for SDN Traffic Monitoring project
# Creates: 4 hosts connected to 1 OpenFlow switch
# =============================================================================

from mininet.topo import Topo


class MonitorTopo(Topo):
    """
    Simple star topology:
    - 1 OpenFlow switch (s1)
    - 4 hosts (h1, h2, h3, h4) each connected to s1
    - All hosts on 10.0.0.x subnet

    Why this topology:
    - Simple enough to understand all traffic flows clearly
    - 4 hosts creates 12 unique src-dst flow pairs, enough to show
      meaningful statistics without being overwhelming
    """

    def build(self):
        # Add the switch
        s1 = self.addSwitch('s1')

        # Add 4 hosts with explicit IPs
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')

        # Connect each host to the switch
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)
        self.addLink(h4, s1)


# This line allows Mininet to find this topology via --custom flag
topos = {'monitortopo': (lambda: MonitorTopo())}
