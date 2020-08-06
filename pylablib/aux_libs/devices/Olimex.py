from ...core.devio import backend  #@UnresolvedImport

import time

_depends_local=["...core.devio.backend"]


class IMCDevice(backend.IBackendWrapper):
    """
    Generic Olimex ATMega device.
    """
    def __init__(self, port_addr, timeout=20.):
        instr=backend.SerialDeviceBackend((port_addr,9600),timeout=timeout,term_write="",connect_on_operation=True)
        backend.IBackendWrapper.__init__(self,instr)
    
    def comm(self, comm, timeout=None):
        comm=comm.strip()
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(comm)
            time.sleep(.1)
            return self.instr.flush_read()
    def query(self, query, timeout=None):
        query=query.strip()
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(query)
            resp=self.instr.readline(timeout=timeout)
            self.instr.flush_read()
        return resp.strip()
    
    

class AVR_IO_M16(IMCDevice):
    """
    Olimex AVR-IO-M16 4x relay board.
    """
    def __init__(self, port_addr, timeout=20.):
        IMCDevice.__init__(self,port_addr,timeout)
        self._add_settings_node("relays",self.get_relays,self.set_relays)
    
    def get_relays(self):
        s=self.query("E")
        if len(s)!=4:
            raise RuntimeError("unexpected response: {}".format(s))
        return [c=="1" for c in s[::-1]]
    def set_relays(self, relays):
        s="".join(["1" if c else "0" for c in relays])[::-1]
        self.comm("W"+s)
        return self.get_relays()
        
    def _set_relay(self, n, v):
        r=self.get_relays()
        r[n]=v
        return self.set_relays(r)[n]
    def open_relay(self, n):
        return self._set_relay(n,True)
    def close_relay(self, n):
        return self._set_relay(n,False)