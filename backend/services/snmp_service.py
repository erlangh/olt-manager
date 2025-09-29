"""
SNMP service for OLT communication.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import ipaddress

try:
    from pysnmp.hlapi.asyncio import *
    from pysnmp.proto.rfc1902 import Integer, OctetString, Counter32, Counter64, Gauge32
    from pysnmp.error import PySnmpError
except ImportError:
    # Fallback for development without pysnmp
    class SnmpEngine: pass
    class CommunityData: pass
    class UdpTransportTarget: pass
    class ContextData: pass
    class ObjectType: pass
    class ObjectIdentity: pass
    class PySnmpError(Exception): pass
    Integer = OctetString = Counter32 = Counter64 = Gauge32 = object

logger = logging.getLogger(__name__)


@dataclass
class SNMPConfig:
    """SNMP configuration."""
    host: str
    port: int = 161
    community: str = "public"
    version: str = "2c"
    timeout: int = 5
    retries: int = 3


@dataclass
class OLTInfo:
    """OLT device information."""
    system_name: str
    system_description: str
    system_uptime: int
    firmware_version: str
    hardware_version: str
    serial_number: str
    mac_address: str
    cpu_usage: float
    memory_usage: float
    temperature: float
    fan_speed: int
    power_consumption: float


@dataclass
class PortInfo:
    """OLT port information."""
    slot: int
    port: int
    admin_status: bool
    oper_status: str
    ont_count: int
    max_ont_count: int
    optical_power_tx: float
    optical_power_rx: float
    temperature: float
    voltage: float
    bias_current: float
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int


@dataclass
class ONTInfo:
    """ONT device information."""
    ont_id: int
    serial_number: str
    status: str
    distance: int
    rx_power: float
    tx_power: float
    voltage: float
    temperature: float
    firmware_version: str
    hardware_version: str
    mac_address: str
    uptime: int
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int


class SNMPService:
    """Base SNMP service class."""
    
    def __init__(self, config: SNMPConfig):
        self.config = config
        self.engine = SnmpEngine()
        self._setup_snmp()
    
    def _setup_snmp(self):
        """Setup SNMP engine and transport."""
        try:
            self.community_data = CommunityData(self.config.community)
            self.transport_target = UdpTransportTarget(
                (self.config.host, self.config.port),
                timeout=self.config.timeout,
                retries=self.config.retries
            )
            self.context_data = ContextData()
        except Exception as e:
            logger.error(f"Failed to setup SNMP: {e}")
            raise
    
    async def get(self, oid: str) -> Optional[Any]:
        """Get single SNMP value."""
        try:
            iterator = getCmd(
                self.engine,
                self.community_data,
                self.transport_target,
                self.context_data,
                ObjectType(ObjectIdentity(oid))
            )
            
            error_indication, error_status, error_index, var_binds = await iterator
            
            if error_indication:
                logger.error(f"SNMP error indication: {error_indication}")
                return None
            
            if error_status:
                logger.error(f"SNMP error status: {error_status.prettyPrint()}")
                return None
            
            for var_bind in var_binds:
                return var_bind[1]
            
        except Exception as e:
            logger.error(f"SNMP get error for OID {oid}: {e}")
            return None
    
    async def get_bulk(self, oids: List[str]) -> Dict[str, Any]:
        """Get multiple SNMP values."""
        results = {}
        
        try:
            object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]
            
            iterator = getCmd(
                self.engine,
                self.community_data,
                self.transport_target,
                self.context_data,
                *object_types
            )
            
            error_indication, error_status, error_index, var_binds = await iterator
            
            if error_indication:
                logger.error(f"SNMP bulk error indication: {error_indication}")
                return results
            
            if error_status:
                logger.error(f"SNMP bulk error status: {error_status.prettyPrint()}")
                return results
            
            for i, var_bind in enumerate(var_binds):
                if i < len(oids):
                    results[oids[i]] = var_bind[1]
            
        except Exception as e:
            logger.error(f"SNMP bulk get error: {e}")
        
        return results
    
    async def walk(self, oid: str) -> Dict[str, Any]:
        """Walk SNMP tree."""
        results = {}
        
        try:
            iterator = nextCmd(
                self.engine,
                self.community_data,
                self.transport_target,
                self.context_data,
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
            
            async for error_indication, error_status, error_index, var_binds in iterator:
                if error_indication:
                    logger.error(f"SNMP walk error indication: {error_indication}")
                    break
                
                if error_status:
                    logger.error(f"SNMP walk error status: {error_status.prettyPrint()}")
                    break
                
                for var_bind in var_binds:
                    oid_str = str(var_bind[0])
                    value = var_bind[1]
                    results[oid_str] = value
            
        except Exception as e:
            logger.error(f"SNMP walk error for OID {oid}: {e}")
        
        return results
    
    async def set(self, oid: str, value: Any, value_type: str = "integer") -> bool:
        """Set SNMP value."""
        try:
            # Convert value based on type
            if value_type == "integer":
                snmp_value = Integer(value)
            elif value_type == "string":
                snmp_value = OctetString(value)
            elif value_type == "gauge":
                snmp_value = Gauge32(value)
            else:
                snmp_value = value
            
            iterator = setCmd(
                self.engine,
                self.community_data,
                self.transport_target,
                self.context_data,
                ObjectType(ObjectIdentity(oid), snmp_value)
            )
            
            error_indication, error_status, error_index, var_binds = await iterator
            
            if error_indication:
                logger.error(f"SNMP set error indication: {error_indication}")
                return False
            
            if error_status:
                logger.error(f"SNMP set error status: {error_status.prettyPrint()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"SNMP set error for OID {oid}: {e}")
            return False


class ZTEOLTService(SNMPService):
    """ZTE C320 OLT specific SNMP service."""
    
    # ZTE C320 specific OIDs
    OID_SYSTEM_NAME = "1.3.6.1.2.1.1.5.0"
    OID_SYSTEM_DESC = "1.3.6.1.2.1.1.1.0"
    OID_SYSTEM_UPTIME = "1.3.6.1.2.1.1.3.0"
    OID_SYSTEM_CONTACT = "1.3.6.1.2.1.1.4.0"
    OID_SYSTEM_LOCATION = "1.3.6.1.2.1.1.6.0"
    
    # Hardware information
    OID_FIRMWARE_VERSION = "1.3.6.1.4.1.3902.1012.3.1.1.1.1.2"
    OID_HARDWARE_VERSION = "1.3.6.1.4.1.3902.1012.3.1.1.1.1.3"
    OID_SERIAL_NUMBER = "1.3.6.1.4.1.3902.1012.3.1.1.1.1.4"
    OID_MAC_ADDRESS = "1.3.6.1.4.1.3902.1012.3.1.1.1.1.5"
    
    # Performance metrics
    OID_CPU_USAGE = "1.3.6.1.4.1.3902.1012.3.1.2.1.1.2"
    OID_MEMORY_USAGE = "1.3.6.1.4.1.3902.1012.3.1.2.1.1.3"
    OID_TEMPERATURE = "1.3.6.1.4.1.3902.1012.3.1.2.1.1.4"
    OID_FAN_SPEED = "1.3.6.1.4.1.3902.1012.3.1.2.1.1.5"
    OID_POWER_CONSUMPTION = "1.3.6.1.4.1.3902.1012.3.1.2.1.1.6"
    
    # Port information
    OID_PORT_ADMIN_STATUS = "1.3.6.1.4.1.3902.1012.3.28.1.1.3"
    OID_PORT_OPER_STATUS = "1.3.6.1.4.1.3902.1012.3.28.1.1.4"
    OID_PORT_ONT_COUNT = "1.3.6.1.4.1.3902.1012.3.28.1.1.5"
    OID_PORT_MAX_ONT = "1.3.6.1.4.1.3902.1012.3.28.1.1.6"
    OID_PORT_OPTICAL_TX = "1.3.6.1.4.1.3902.1012.3.28.1.1.7"
    OID_PORT_OPTICAL_RX = "1.3.6.1.4.1.3902.1012.3.28.1.1.8"
    OID_PORT_TEMPERATURE = "1.3.6.1.4.1.3902.1012.3.28.1.1.9"
    OID_PORT_VOLTAGE = "1.3.6.1.4.1.3902.1012.3.28.1.1.10"
    OID_PORT_BIAS_CURRENT = "1.3.6.1.4.1.3902.1012.3.28.1.1.11"
    
    # Port statistics
    OID_PORT_RX_BYTES = "1.3.6.1.4.1.3902.1012.3.28.2.1.2"
    OID_PORT_TX_BYTES = "1.3.6.1.4.1.3902.1012.3.28.2.1.3"
    OID_PORT_RX_PACKETS = "1.3.6.1.4.1.3902.1012.3.28.2.1.4"
    OID_PORT_TX_PACKETS = "1.3.6.1.4.1.3902.1012.3.28.2.1.5"
    OID_PORT_RX_ERRORS = "1.3.6.1.4.1.3902.1012.3.28.2.1.6"
    OID_PORT_TX_ERRORS = "1.3.6.1.4.1.3902.1012.3.28.2.1.7"
    
    # ONT information
    OID_ONT_STATUS = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.10"
    OID_ONT_DISTANCE = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.11"
    OID_ONT_RX_POWER = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.12"
    OID_ONT_TX_POWER = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.13"
    OID_ONT_VOLTAGE = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.14"
    OID_ONT_TEMPERATURE = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.15"
    OID_ONT_SERIAL = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.3"
    OID_ONT_FIRMWARE = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.16"
    OID_ONT_HARDWARE = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.17"
    OID_ONT_MAC = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.18"
    OID_ONT_UPTIME = "1.3.6.1.4.1.3902.1012.3.50.12.1.1.19"
    
    # ONT statistics
    OID_ONT_RX_BYTES = "1.3.6.1.4.1.3902.1012.3.50.13.1.1.2"
    OID_ONT_TX_BYTES = "1.3.6.1.4.1.3902.1012.3.50.13.1.1.3"
    OID_ONT_RX_PACKETS = "1.3.6.1.4.1.3902.1012.3.50.13.1.1.4"
    OID_ONT_TX_PACKETS = "1.3.6.1.4.1.3902.1012.3.50.13.1.1.5"
    
    # Configuration OIDs
    OID_ONT_PROVISION = "1.3.6.1.4.1.3902.1012.3.50.11.2.1.1"
    OID_ONT_REBOOT = "1.3.6.1.4.1.3902.1012.3.50.11.3.1.1"
    OID_PORT_ENABLE = "1.3.6.1.4.1.3902.1012.3.28.1.1.20"
    
    def __init__(self, config: SNMPConfig):
        super().__init__(config)
        self.device_cache = {}
        self.cache_timeout = timedelta(minutes=5)
    
    async def discover_olt(self) -> Optional[OLTInfo]:
        """Discover OLT device information."""
        try:
            logger.info(f"Discovering OLT at {self.config.host}")
            
            # Get basic system information
            system_oids = [
                self.OID_SYSTEM_NAME,
                self.OID_SYSTEM_DESC,
                self.OID_SYSTEM_UPTIME,
                self.OID_FIRMWARE_VERSION,
                self.OID_HARDWARE_VERSION,
                self.OID_SERIAL_NUMBER,
                self.OID_MAC_ADDRESS
            ]
            
            system_data = await self.get_bulk(system_oids)
            
            # Get performance metrics
            perf_oids = [
                self.OID_CPU_USAGE,
                self.OID_MEMORY_USAGE,
                self.OID_TEMPERATURE,
                self.OID_FAN_SPEED,
                self.OID_POWER_CONSUMPTION
            ]
            
            perf_data = await self.get_bulk(perf_oids)
            
            # Parse and return OLT info
            olt_info = OLTInfo(
                system_name=str(system_data.get(self.OID_SYSTEM_NAME, "")),
                system_description=str(system_data.get(self.OID_SYSTEM_DESC, "")),
                system_uptime=int(system_data.get(self.OID_SYSTEM_UPTIME, 0)),
                firmware_version=str(system_data.get(self.OID_FIRMWARE_VERSION, "")),
                hardware_version=str(system_data.get(self.OID_HARDWARE_VERSION, "")),
                serial_number=str(system_data.get(self.OID_SERIAL_NUMBER, "")),
                mac_address=str(system_data.get(self.OID_MAC_ADDRESS, "")),
                cpu_usage=float(perf_data.get(self.OID_CPU_USAGE, 0)),
                memory_usage=float(perf_data.get(self.OID_MEMORY_USAGE, 0)),
                temperature=float(perf_data.get(self.OID_TEMPERATURE, 0)),
                fan_speed=int(perf_data.get(self.OID_FAN_SPEED, 0)),
                power_consumption=float(perf_data.get(self.OID_POWER_CONSUMPTION, 0))
            )
            
            logger.info(f"Successfully discovered OLT: {olt_info.system_name}")
            return olt_info
            
        except Exception as e:
            logger.error(f"Failed to discover OLT: {e}")
            return None
    
    async def get_port_info(self, slot: int, port: int) -> Optional[PortInfo]:
        """Get specific port information."""
        try:
            port_index = f"{slot}.{port}"
            
            # Build OIDs with port index
            port_oids = [
                f"{self.OID_PORT_ADMIN_STATUS}.{port_index}",
                f"{self.OID_PORT_OPER_STATUS}.{port_index}",
                f"{self.OID_PORT_ONT_COUNT}.{port_index}",
                f"{self.OID_PORT_MAX_ONT}.{port_index}",
                f"{self.OID_PORT_OPTICAL_TX}.{port_index}",
                f"{self.OID_PORT_OPTICAL_RX}.{port_index}",
                f"{self.OID_PORT_TEMPERATURE}.{port_index}",
                f"{self.OID_PORT_VOLTAGE}.{port_index}",
                f"{self.OID_PORT_BIAS_CURRENT}.{port_index}",
                f"{self.OID_PORT_RX_BYTES}.{port_index}",
                f"{self.OID_PORT_TX_BYTES}.{port_index}",
                f"{self.OID_PORT_RX_PACKETS}.{port_index}",
                f"{self.OID_PORT_TX_PACKETS}.{port_index}",
                f"{self.OID_PORT_RX_ERRORS}.{port_index}",
                f"{self.OID_PORT_TX_ERRORS}.{port_index}"
            ]
            
            port_data = await self.get_bulk(port_oids)
            
            if not port_data:
                return None
            
            port_info = PortInfo(
                slot=slot,
                port=port,
                admin_status=bool(port_data.get(f"{self.OID_PORT_ADMIN_STATUS}.{port_index}", 0)),
                oper_status="up" if port_data.get(f"{self.OID_PORT_OPER_STATUS}.{port_index}", 0) == 1 else "down",
                ont_count=int(port_data.get(f"{self.OID_PORT_ONT_COUNT}.{port_index}", 0)),
                max_ont_count=int(port_data.get(f"{self.OID_PORT_MAX_ONT}.{port_index}", 0)),
                optical_power_tx=float(port_data.get(f"{self.OID_PORT_OPTICAL_TX}.{port_index}", 0)) / 100,
                optical_power_rx=float(port_data.get(f"{self.OID_PORT_OPTICAL_RX}.{port_index}", 0)) / 100,
                temperature=float(port_data.get(f"{self.OID_PORT_TEMPERATURE}.{port_index}", 0)) / 100,
                voltage=float(port_data.get(f"{self.OID_PORT_VOLTAGE}.{port_index}", 0)) / 1000,
                bias_current=float(port_data.get(f"{self.OID_PORT_BIAS_CURRENT}.{port_index}", 0)) / 1000,
                rx_bytes=int(port_data.get(f"{self.OID_PORT_RX_BYTES}.{port_index}", 0)),
                tx_bytes=int(port_data.get(f"{self.OID_PORT_TX_BYTES}.{port_index}", 0)),
                rx_packets=int(port_data.get(f"{self.OID_PORT_RX_PACKETS}.{port_index}", 0)),
                tx_packets=int(port_data.get(f"{self.OID_PORT_TX_PACKETS}.{port_index}", 0)),
                rx_errors=int(port_data.get(f"{self.OID_PORT_RX_ERRORS}.{port_index}", 0)),
                tx_errors=int(port_data.get(f"{self.OID_PORT_TX_ERRORS}.{port_index}", 0))
            )
            
            return port_info
            
        except Exception as e:
            logger.error(f"Failed to get port info for {slot}/{port}: {e}")
            return None
    
    async def get_ont_info(self, slot: int, port: int, ont_id: int) -> Optional[ONTInfo]:
        """Get specific ONT information."""
        try:
            ont_index = f"{slot}.{port}.{ont_id}"
            
            # Build OIDs with ONT index
            ont_oids = [
                f"{self.OID_ONT_STATUS}.{ont_index}",
                f"{self.OID_ONT_DISTANCE}.{ont_index}",
                f"{self.OID_ONT_RX_POWER}.{ont_index}",
                f"{self.OID_ONT_TX_POWER}.{ont_index}",
                f"{self.OID_ONT_VOLTAGE}.{ont_index}",
                f"{self.OID_ONT_TEMPERATURE}.{ont_index}",
                f"{self.OID_ONT_SERIAL}.{ont_index}",
                f"{self.OID_ONT_FIRMWARE}.{ont_index}",
                f"{self.OID_ONT_HARDWARE}.{ont_index}",
                f"{self.OID_ONT_MAC}.{ont_index}",
                f"{self.OID_ONT_UPTIME}.{ont_index}",
                f"{self.OID_ONT_RX_BYTES}.{ont_index}",
                f"{self.OID_ONT_TX_BYTES}.{ont_index}",
                f"{self.OID_ONT_RX_PACKETS}.{ont_index}",
                f"{self.OID_ONT_TX_PACKETS}.{ont_index}"
            ]
            
            ont_data = await self.get_bulk(ont_oids)
            
            if not ont_data:
                return None
            
            # Parse status
            status_code = int(ont_data.get(f"{self.OID_ONT_STATUS}.{ont_index}", 0))
            status_map = {1: "online", 2: "offline", 3: "dying_gasp", 4: "los"}
            status = status_map.get(status_code, "unknown")
            
            ont_info = ONTInfo(
                ont_id=ont_id,
                serial_number=str(ont_data.get(f"{self.OID_ONT_SERIAL}.{ont_index}", "")),
                status=status,
                distance=int(ont_data.get(f"{self.OID_ONT_DISTANCE}.{ont_index}", 0)),
                rx_power=float(ont_data.get(f"{self.OID_ONT_RX_POWER}.{ont_index}", 0)) / 100,
                tx_power=float(ont_data.get(f"{self.OID_ONT_TX_POWER}.{ont_index}", 0)) / 100,
                voltage=float(ont_data.get(f"{self.OID_ONT_VOLTAGE}.{ont_index}", 0)) / 1000,
                temperature=float(ont_data.get(f"{self.OID_ONT_TEMPERATURE}.{ont_index}", 0)) / 100,
                firmware_version=str(ont_data.get(f"{self.OID_ONT_FIRMWARE}.{ont_index}", "")),
                hardware_version=str(ont_data.get(f"{self.OID_ONT_HARDWARE}.{ont_index}", "")),
                mac_address=str(ont_data.get(f"{self.OID_ONT_MAC}.{ont_index}", "")),
                uptime=int(ont_data.get(f"{self.OID_ONT_UPTIME}.{ont_index}", 0)),
                rx_bytes=int(ont_data.get(f"{self.OID_ONT_RX_BYTES}.{ont_index}", 0)),
                tx_bytes=int(ont_data.get(f"{self.OID_ONT_TX_BYTES}.{ont_index}", 0)),
                rx_packets=int(ont_data.get(f"{self.OID_ONT_RX_PACKETS}.{ont_index}", 0)),
                tx_packets=int(ont_data.get(f"{self.OID_ONT_TX_PACKETS}.{ont_index}", 0))
            )
            
            return ont_info
            
        except Exception as e:
            logger.error(f"Failed to get ONT info for {slot}/{port}/{ont_id}: {e}")
            return None
    
    async def discover_all_ports(self) -> List[PortInfo]:
        """Discover all ports on the OLT."""
        ports = []
        
        try:
            # Walk port admin status to find all ports
            port_status_data = await self.walk(self.OID_PORT_ADMIN_STATUS)
            
            for oid, value in port_status_data.items():
                # Extract slot and port from OID
                oid_parts = oid.split('.')
                if len(oid_parts) >= 2:
                    try:
                        slot = int(oid_parts[-2])
                        port = int(oid_parts[-1])
                        
                        port_info = await self.get_port_info(slot, port)
                        if port_info:
                            ports.append(port_info)
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"Discovered {len(ports)} ports")
            return ports
            
        except Exception as e:
            logger.error(f"Failed to discover ports: {e}")
            return []
    
    async def discover_all_onts(self, slot: int, port: int) -> List[ONTInfo]:
        """Discover all ONTs on a specific port."""
        onts = []
        
        try:
            # Walk ONT status for the specific port
            ont_status_oid = f"{self.OID_ONT_STATUS}.{slot}.{port}"
            ont_status_data = await self.walk(ont_status_oid)
            
            for oid, value in ont_status_data.items():
                # Extract ONT ID from OID
                oid_parts = oid.split('.')
                if len(oid_parts) >= 1:
                    try:
                        ont_id = int(oid_parts[-1])
                        
                        ont_info = await self.get_ont_info(slot, port, ont_id)
                        if ont_info:
                            onts.append(ont_info)
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"Discovered {len(onts)} ONTs on port {slot}/{port}")
            return onts
            
        except Exception as e:
            logger.error(f"Failed to discover ONTs on port {slot}/{port}: {e}")
            return []
    
    async def provision_ont(self, slot: int, port: int, ont_id: int, serial_number: str) -> bool:
        """Provision ONT on the OLT."""
        try:
            ont_index = f"{slot}.{port}.{ont_id}"
            provision_oid = f"{self.OID_ONT_PROVISION}.{ont_index}"
            
            # Set ONT serial number for provisioning
            success = await self.set(provision_oid, serial_number, "string")
            
            if success:
                logger.info(f"Successfully provisioned ONT {serial_number} at {slot}/{port}/{ont_id}")
            else:
                logger.error(f"Failed to provision ONT {serial_number} at {slot}/{port}/{ont_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error provisioning ONT: {e}")
            return False
    
    async def reboot_ont(self, slot: int, port: int, ont_id: int) -> bool:
        """Reboot specific ONT."""
        try:
            ont_index = f"{slot}.{port}.{ont_id}"
            reboot_oid = f"{self.OID_ONT_REBOOT}.{ont_index}"
            
            # Send reboot command (value 1 = reboot)
            success = await self.set(reboot_oid, 1, "integer")
            
            if success:
                logger.info(f"Successfully rebooted ONT at {slot}/{port}/{ont_id}")
            else:
                logger.error(f"Failed to reboot ONT at {slot}/{port}/{ont_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rebooting ONT: {e}")
            return False
    
    async def enable_port(self, slot: int, port: int, enable: bool = True) -> bool:
        """Enable or disable OLT port."""
        try:
            port_index = f"{slot}.{port}"
            enable_oid = f"{self.OID_PORT_ENABLE}.{port_index}"
            
            # Set port admin status (1 = enable, 2 = disable)
            value = 1 if enable else 2
            success = await self.set(enable_oid, value, "integer")
            
            action = "enabled" if enable else "disabled"
            if success:
                logger.info(f"Successfully {action} port {slot}/{port}")
            else:
                logger.error(f"Failed to {action} port {slot}/{port}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting port status: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test SNMP connection to OLT."""
        try:
            system_name = await self.get(self.OID_SYSTEM_NAME)
            return system_name is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False