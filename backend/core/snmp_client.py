from pysnmp.hlapi import *
from pysnmp.error import PySnmpError
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from loguru import logger
from core.config import settings

class ZTE_C320_SNMP:
    """SNMP client specifically designed for ZTE C320 OLT management."""
    
    # ZTE C320 specific OIDs
    OLT_SYSTEM_INFO = {
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysLocation': '1.3.6.1.2.1.1.6.0',
    }
    
    # Port/Interface OIDs
    PORT_OIDS = {
        'ifDescr': '1.3.6.1.2.1.2.2.1.2',
        'ifType': '1.3.6.1.2.1.2.2.1.3',
        'ifMtu': '1.3.6.1.2.1.2.2.1.4',
        'ifSpeed': '1.3.6.1.2.1.2.2.1.5',
        'ifPhysAddress': '1.3.6.1.2.1.2.2.1.6',
        'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',
        'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
        'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
        'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
    }
    
    # ONT specific OIDs for ZTE C320
    ONT_OIDS = {
        'ontSerialNumber': '1.3.6.1.4.1.3902.1012.3.28.1.1.5',
        'ontStatus': '1.3.6.1.4.1.3902.1012.3.28.1.1.1',
        'ontDistance': '1.3.6.1.4.1.3902.1012.3.28.1.1.8',
        'ontRxPower': '1.3.6.1.4.1.3902.1012.3.28.1.1.27',
        'ontTxPower': '1.3.6.1.4.1.3902.1012.3.28.1.1.28',
        'ontModel': '1.3.6.1.4.1.3902.1012.3.28.1.1.4',
        'ontVersion': '1.3.6.1.4.1.3902.1012.3.28.1.1.21',
    }
    
    # Performance monitoring OIDs
    PERFORMANCE_OIDS = {
        'cpuUtilization': '1.3.6.1.4.1.3902.1012.3.1.1.1.1.7',
        'memoryUtilization': '1.3.6.1.4.1.3902.1012.3.1.1.1.1.8',
        'temperature': '1.3.6.1.4.1.3902.1012.3.1.1.1.1.9',
        'fanStatus': '1.3.6.1.4.1.3902.1012.3.1.1.1.1.10',
    }
    
    def __init__(self, host: str, community: str = "public", port: int = 161, version: str = "2c"):
        self.host = host
        self.community = community
        self.port = port
        self.version = version
        self.timeout = settings.SNMP_TIMEOUT
        self.retries = settings.SNMP_RETRIES
    
    def _get_snmp_engine(self):
        """Create SNMP engine based on version."""
        if self.version == "1":
            return CommunityData(self.community, mpModel=0)
        elif self.version == "2c":
            return CommunityData(self.community, mpModel=1)
        else:
            raise ValueError(f"Unsupported SNMP version: {self.version}")
    
    async def get(self, oid: str) -> Optional[Any]:
        """Get single OID value."""
        try:
            iterator = getCmd(
                SnmpEngine(),
                self._get_snmp_engine(),
                UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                logger.error(f"SNMP error indication: {errorIndication}")
                return None
            elif errorStatus:
                logger.error(f"SNMP error status: {errorStatus.prettyPrint()}")
                return None
            else:
                for varBind in varBinds:
                    return varBind[1].prettyPrint()
        except Exception as e:
            logger.error(f"SNMP GET error for {oid}: {str(e)}")
            return None
    
    async def walk(self, oid: str) -> Dict[str, Any]:
        """Walk OID tree and return all values."""
        results = {}
        try:
            iterator = nextCmd(
                SnmpEngine(),
                self._get_snmp_engine(),
                UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
            
            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication:
                    logger.error(f"SNMP walk error indication: {errorIndication}")
                    break
                elif errorStatus:
                    logger.error(f"SNMP walk error status: {errorStatus.prettyPrint()}")
                    break
                else:
                    for varBind in varBinds:
                        oid_str = varBind[0].prettyPrint()
                        value = varBind[1].prettyPrint()
                        results[oid_str] = value
        except Exception as e:
            logger.error(f"SNMP WALK error for {oid}: {str(e)}")
        
        return results
    
    async def set(self, oid: str, value: Any, value_type: str = "OctetString") -> bool:
        """Set OID value."""
        try:
            # Map value types
            type_map = {
                "Integer": Integer,
                "OctetString": OctetString,
                "IpAddress": IpAddress,
                "Counter32": Counter32,
                "Gauge32": Gauge32,
                "TimeTicks": TimeTicks,
            }
            
            if value_type not in type_map:
                logger.error(f"Unsupported value type: {value_type}")
                return False
            
            iterator = setCmd(
                SnmpEngine(),
                self._get_snmp_engine(),
                UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid), type_map[value_type](value))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                logger.error(f"SNMP SET error indication: {errorIndication}")
                return False
            elif errorStatus:
                logger.error(f"SNMP SET error status: {errorStatus.prettyPrint()}")
                return False
            else:
                logger.info(f"SNMP SET successful for {oid} = {value}")
                return True
        except Exception as e:
            logger.error(f"SNMP SET error for {oid}: {str(e)}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get OLT system information."""
        info = {}
        for key, oid in self.OLT_SYSTEM_INFO.items():
            value = await self.get(oid)
            if value:
                info[key] = value
        return info
    
    async def get_port_list(self) -> List[Dict[str, Any]]:
        """Get list of all ports with their information."""
        ports = []
        
        # Get interface descriptions to identify GPON ports
        if_descr_data = await self.walk(self.PORT_OIDS['ifDescr'])
        
        for oid, description in if_descr_data.items():
            if 'gpon' in description.lower() or 'pon' in description.lower():
                # Extract interface index from OID
                if_index = oid.split('.')[-1]
                
                port_info = {
                    'index': if_index,
                    'description': description,
                }
                
                # Get additional port information
                for key, base_oid in self.PORT_OIDS.items():
                    if key != 'ifDescr':
                        value = await self.get(f"{base_oid}.{if_index}")
                        if value:
                            port_info[key] = value
                
                ports.append(port_info)
        
        return ports
    
    async def get_ont_list(self, port_index: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of ONTs, optionally filtered by port."""
        onts = []
        
        # Walk ONT status table
        ont_status_data = await self.walk(self.ONT_OIDS['ontStatus'])
        
        for oid, status in ont_status_data.items():
            # Extract port and ONT ID from OID
            oid_parts = oid.split('.')
            if len(oid_parts) >= 2:
                port_id = oid_parts[-2]
                ont_id = oid_parts[-1]
                
                # Filter by port if specified
                if port_index and int(port_id) != port_index:
                    continue
                
                ont_info = {
                    'port_id': port_id,
                    'ont_id': ont_id,
                    'status': status,
                }
                
                # Get additional ONT information
                for key, base_oid in self.ONT_OIDS.items():
                    if key != 'ontStatus':
                        ont_oid = f"{base_oid}.{port_id}.{ont_id}"
                        value = await self.get(ont_oid)
                        if value:
                            ont_info[key] = value
                
                onts.append(ont_info)
        
        return onts
    
    async def get_performance_data(self) -> Dict[str, Any]:
        """Get OLT performance data."""
        performance = {}
        
        for key, oid in self.PERFORMANCE_OIDS.items():
            value = await self.get(oid)
            if value:
                performance[key] = value
        
        return performance
    
    async def provision_ont(self, port_id: int, ont_id: int, serial_number: str, profile: str = "default") -> bool:
        """Provision a new ONT."""
        try:
            # ZTE C320 specific provisioning OIDs and procedures
            # This is a simplified example - actual implementation would depend on specific ZTE MIBs
            
            # Set ONT serial number
            serial_oid = f"1.3.6.1.4.1.3902.1012.3.28.2.1.3.{port_id}.{ont_id}"
            if not await self.set(serial_oid, serial_number, "OctetString"):
                return False
            
            # Set ONT profile
            profile_oid = f"1.3.6.1.4.1.3902.1012.3.28.2.1.4.{port_id}.{ont_id}"
            if not await self.set(profile_oid, profile, "OctetString"):
                return False
            
            # Activate ONT
            activate_oid = f"1.3.6.1.4.1.3902.1012.3.28.2.1.1.{port_id}.{ont_id}"
            if not await self.set(activate_oid, 1, "Integer"):
                return False
            
            logger.info(f"ONT provisioned successfully: Port {port_id}, ONT {ont_id}, SN {serial_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error provisioning ONT: {str(e)}")
            return False
    
    async def delete_ont(self, port_id: int, ont_id: int) -> bool:
        """Delete an ONT."""
        try:
            # Deactivate ONT
            deactivate_oid = f"1.3.6.1.4.1.3902.1012.3.28.2.1.1.{port_id}.{ont_id}"
            if await self.set(deactivate_oid, 2, "Integer"):  # 2 = deactivate
                logger.info(f"ONT deleted successfully: Port {port_id}, ONT {ont_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting ONT: {str(e)}")
            return False
    
    async def test_connection(self) -> bool:
        """Test SNMP connection to OLT."""
        try:
            result = await self.get(self.OLT_SYSTEM_INFO['sysDescr'])
            return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False