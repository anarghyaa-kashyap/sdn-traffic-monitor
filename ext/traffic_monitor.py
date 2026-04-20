# =============================================================================
# traffic_monitor.py - POX SDN Controller
# Traffic Monitoring and Statistics Collector
# Protocol: OpenFlow 1.0 | Controller: POX
# =============================================================================

from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
from pox.lib.recoco import Timer
import datetime

log = core.getLogger()
STATS_INTERVAL = 10


class TrafficMonitor(EventMixin):
    """
    POX controller that:
    1. Acts as a learning switch (MAC to port mapping)
    2. Installs flow rules for known destinations
    3. Every 10 seconds polls all switches for flow statistics
    4. Displays packet/byte counts and writes to traffic_report.txt
    """

    def __init__(self):
        self.mac_to_port = {}
        self.connections = {}

        self.report_file = open("traffic_report.txt", "w")
        self.report_file.write("=" * 60 + "\n")
        self.report_file.write("  SDN Traffic Monitoring Report\n")
        self.report_file.write("  Started: {}\n".format(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.report_file.write("=" * 60 + "\n")
        self.report_file.flush()

        core.openflow.addListeners(self)
        Timer(STATS_INTERVAL, self._request_stats, recurring=True)
        log.info("TrafficMonitor started. Polling every %s seconds.", STATS_INTERVAL)

    def _request_stats(self):
        """Send flow stats request to every connected switch."""
        for dpid, conn in self.connections.items():
            log.info("Polling stats from switch: %s", dpidToStr(dpid))
            msg = of.ofp_stats_request(body=of.ofp_flow_stats_request())
            conn.send(msg)

    def _handle_ConnectionUp(self, event):
        """Called when a switch connects to this controller."""
        dpid = event.dpid
        self.connections[dpid] = event.connection
        self.mac_to_port[dpid] = {}
        log.info("Switch connected: %s", dpidToStr(dpid))

        msg = of.ofp_flow_mod()
        msg.priority = 0
        msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        event.connection.send(msg)

    def _handle_ConnectionDown(self, event):
        """Called when a switch disconnects."""
        dpid = event.dpid
        if dpid in self.connections:
            del self.connections[dpid]
        log.info("Switch disconnected: %s", dpidToStr(dpid))

    def _handle_PacketIn(self, event):
        """
        Called when switch sends unmatched packet to controller.
        1. Learn source MAC and port
        2. If destination known, install flow rule
        3. Otherwise flood
        """
        packet = event.parsed
        if not packet.parsed:
            return

        dpid = event.dpid
        in_port = event.port
        src_mac = str(packet.src)
        dst_mac = str(packet.dst)

        self.mac_to_port[dpid][src_mac] = in_port

        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]

            msg = of.ofp_flow_mod()
            msg.match.dl_src = packet.src
            msg.match.dl_dst = packet.dst
            msg.match.in_port = in_port
            msg.priority = 1
            msg.idle_timeout = 30
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)

            log.debug("Flow installed: %s -> %s on port %s", src_mac, dst_mac, out_port)
        else:
            out_port = of.OFPP_FLOOD

        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(msg)

    def _handle_FlowStatsReceived(self, event):
        """
        Called when switch replies with flow statistics.
        Displays and logs packet/byte counts per flow.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dpid = dpidToStr(event.connection.dpid)
        stats = event.stats

        log.info("")
        log.info("=" * 60)
        log.info("[%s] Flow Stats - Switch DPID: %s", timestamp, dpid)
        log.info("=" * 60)
        log.info("  %-10s %-15s %-15s", "Priority", "Packets", "Bytes")
        log.info("-" * 60)

        self.report_file.write("\n" + "=" * 60 + "\n")
        self.report_file.write("[{}] Flow Stats - Switch DPID: {}\n".format(timestamp, dpid))
        self.report_file.write("=" * 60 + "\n")
        self.report_file.write("  {:<10} {:<15} {:<15}\n".format("Priority", "Packets", "Bytes"))
        self.report_file.write("-" * 60 + "\n")

        for flow in sorted(stats, key=lambda f: f.byte_count, reverse=True):
            line = "  {:<10} {:<15} {:<15}".format(
                flow.priority,
                flow.packet_count,
                flow.byte_count
            )
            log.info(line)
            self.report_file.write(line + "\n")

        total_packets = sum(f.packet_count for f in stats)
        total_bytes = sum(f.byte_count for f in stats)
        summary = "  TOTAL: {} packets | {} bytes across {} flows".format(
            total_packets, total_bytes, len(stats)
        )
        log.info("-" * 60)
        log.info(summary)
        self.report_file.write("-" * 60 + "\n")
        self.report_file.write(summary + "\n")
        self.report_file.flush()


def launch():
    """Entry point for POX - called when module is loaded."""
    core.registerNew(TrafficMonitor)
    log.info("Traffic Monitor module loaded.")
