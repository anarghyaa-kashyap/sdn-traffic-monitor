# =============================================================================
# traffic_monitor.py
# SDN Traffic Monitoring and Statistics Collector
# Controller: Ryu | Protocol: OpenFlow 1.3
#
# What this does:
#   1. Acts as a learning switch (builds MAC-to-port table dynamically)
#   2. Installs flow rules on switches for known destinations
#   3. Every 10 seconds, polls all connected switches for flow statistics
#   4. Displays packet/byte counts per flow in terminal
#   5. Writes timestamped reports to traffic_report.txt
# =============================================================================

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.lib import hub
import datetime

# How often to request statistics from switches (in seconds)
STATS_INTERVAL = 10


class TrafficMonitor(app_manager.RyuApp):
    """
    Ryu controller application that combines:
    - Learning switch (Layer 2 forwarding)
    - Periodic flow statistics collection and reporting
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficMonitor, self).__init__(*args, **kwargs)

        # MAC address table: {switch_id: {mac_address: port_number}}
        self.mac_to_port = {}

        # All connected switches: {switch_id: datapath_object}
        self.datapaths = {}

        # Open report file for writing (created fresh each run)
        self.report_file = open("traffic_report.txt", "w")
        self.report_file.write("=" * 60 + "\n")
        self.report_file.write("  SDN Traffic Monitoring Report\n")
        self.report_file.write("  Started: {}\n".format(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.report_file.write("=" * 60 + "\n")

        # Spawn background thread that polls stats every STATS_INTERVAL seconds
        self.monitor_thread = hub.spawn(self._monitor)

    # -------------------------------------------------------------------------
    # BACKGROUND MONITORING LOOP
    # -------------------------------------------------------------------------

    def _monitor(self):
        """
        Background thread function.
        Runs forever: every STATS_INTERVAL seconds, request stats
        from every connected switch.
        """
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(STATS_INTERVAL)

    def _request_stats(self, datapath):
        """
        Send OFPFlowStatsRequest to a switch.
        The switch will reply with OFPFlowStatsReply (handled below).
        """
        self.logger.info("Polling stats from switch DPID: %s", datapath.id)
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # -------------------------------------------------------------------------
    # SWITCH CONNECTION HANDLER
    # -------------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Called automatically when a switch connects to this controller.
        Installs a table-miss rule: any packet with no matching flow rule
        gets sent to the controller (triggering packet_in).
        Also registers the switch in self.datapaths for stats polling.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Register this switch
        self.datapaths[datapath.id] = datapath
        self.logger.info("Switch connected — DPID: %s", datapath.id)

        # Table-miss flow rule: priority 0, match anything, send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self._add_flow(datapath, priority=0, match=match, actions=actions)

    # -------------------------------------------------------------------------
    # FLOW RULE HELPER
    # -------------------------------------------------------------------------

    def _add_flow(self, datapath, priority, match, actions,
                  idle_timeout=0, hard_timeout=0):
        """
        Install a flow rule on a switch.

        Args:
            datapath: the switch object
            priority: higher number = higher priority (table-miss uses 0)
            match: OFPMatch object defining what packets this rule catches
            actions: list of actions to apply (e.g. output on a port)
            idle_timeout: delete rule after this many seconds of inactivity
            hard_timeout: delete rule after this many seconds regardless
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    # -------------------------------------------------------------------------
    # PACKET-IN HANDLER (Learning Switch Logic)
    # -------------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Called when a switch sends a packet to the controller
        because no flow rule matched it.

        Logic:
        1. Learn source MAC → port mapping
        2. If destination MAC is known, install a flow rule for future packets
        3. If destination unknown, flood the packet
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignore LLDP packets (link layer discovery, not user traffic)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst_mac = eth.dst
        src_mac = eth.src
        dpid = datapath.id

        # Initialize MAC table for this switch if first time
        self.mac_to_port.setdefault(dpid, {})

        # LEARN: record which port this source MAC came from
        self.mac_to_port[dpid][src_mac] = in_port

        # DECIDE: do we know where the destination is?
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD  # destination unknown, flood

        actions = [parser.OFPActionOutput(out_port)]

        # INSTALL FLOW RULE: only if we know the destination port
        # idle_timeout=30 means rule deleted after 30s of no traffic
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst_mac,
                eth_src=src_mac
            )
            self._add_flow(
                datapath, priority=1,
                match=match, actions=actions,
                idle_timeout=30
            )

        # FORWARD: send this specific packet out (even before rule takes effect)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)

    # -------------------------------------------------------------------------
    # FLOW STATISTICS REPLY HANDLER
    # -------------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """
        Called when a switch replies to our OFPFlowStatsRequest.
        Receives statistics for every flow rule currently on that switch.
        Displays them in terminal and writes to traffic_report.txt.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        # --- Terminal output ---
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("[%s] Flow Stats — Switch DPID: %s", timestamp, dpid)
        self.logger.info("=" * 60)
        self.logger.info(
            "  %-10s %-15s %-15s %s",
            "Priority", "Packets", "Bytes", "Match"
        )
        self.logger.info("-" * 60)

        # --- Report file output ---
        self.report_file.write("\n" + "=" * 60 + "\n")
        self.report_file.write(
            "[{}] Flow Stats — Switch DPID: {}\n".format(timestamp, dpid)
        )
        self.report_file.write("=" * 60 + "\n")
        self.report_file.write(
            "  {:<10} {:<15} {:<15} {}\n".format(
                "Priority", "Packets", "Bytes", "Match"
            )
        )
        self.report_file.write("-" * 60 + "\n")

        # Sort by byte count descending so heaviest flows appear first
        for stat in sorted(body, key=lambda s: s.byte_count, reverse=True):
            line_terminal = "  {:<10} {:<15} {:<15} {}".format(
                stat.priority,
                stat.packet_count,
                stat.byte_count,
                str(stat.match)
            )
            line_file = "  {:<10} {:<15} {:<15} {}\n".format(
                stat.priority,
                stat.packet_count,
                stat.byte_count,
                str(stat.match)
            )
            self.logger.info(line_terminal)
            self.report_file.write(line_file)

        # Summary line
        total_packets = sum(s.packet_count for s in body)
        total_bytes = sum(s.byte_count for s in body)
        summary = "  TOTAL: {} packets | {} bytes across {} flows".format(
            total_packets, total_bytes, len(body)
        )
        self.logger.info("-" * 60)
        self.logger.info(summary)
        self.report_file.write("-" * 60 + "\n")
        self.report_file.write(summary + "\n")

        # Flush so file is always up to date even mid-experiment
        self.report_file.flush()
