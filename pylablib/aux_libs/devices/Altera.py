"""
Home-built Altera NIOS soft-core device.
"""

from ...core.devio import backend  #@UnresolvedImport
from ...core.utils import numerical  #@UnresolvedImport

import struct, math, time

import numpy as np

_depends_local=["...core.devio.backend"]


def float_to_sfixed(val, high, low):
    l=high-low+1
    val=val/(2.**low)
    ival=int(math.ceil(val))
    ival=numerical.limit_to_range(ival,-(1<<(l-1)),(1<<(l-1))-1)
    ival=ival%(1<<l)
    return ival
def float_to_ufixed(val, high, low):
    l=high-low+1
    val=val/(2**low)
    ival=int(math.ceil(val))
    ival=numerical.limit_to_range(ival,0,(1<<l)-1)
    return ival
    
def sfixed_to_float(ival, high, low):
    l=high-low+1
    ival=ival%int(2**l)
    if ival>=int(2**(l-1)):
        ival=ival-2**l
    return ival*(2**low)
def ufixed_to_float(ival, high, low):
    l=high-low+1
    ival=ival%int(2**l)
    return ival*(2**low)
    

class NIOSDevice(backend.IBackendWrapper):
    def __init__(self, port_addr, timeout=3.):
        instr=backend.SerialDeviceBackend((port_addr,57600),timeout=timeout,term_write="",term_read="\n",connect_on_operation=True)
        backend.IBackendWrapper.__init__(self,instr)
    
    _ops={"nop":0x00,"reset":0x01,
          "read_memreg":0x10,"read_mmapreg":0x11,"write_memreg":0x18,
          "read_stream":0x20,"write_stream":0x28,
          "periph_comm":0x40,"debug":0xE0}
    @staticmethod
    def _build_comm_msg(op, addr, p1, p2):
        op=NIOSDevice._ops.get(op,op)
        return struct.pack("<H",op&0xFFFF)+struct.pack("<H",addr&0xFFFF)+struct.pack("<I",p1&0xFFFFFFFF)+struct.pack("<I",p2&0xFFFFFFFF)
    @staticmethod
    def _check_response(resp):
        if resp.startswith("OK"):
            return resp
        if resp.startswith("ERR"):
            raise RuntimeError("command returned error: {}".format(resp))
        raise ValueError("unrecognized response: {}".format(resp))
    def _send_read(self, msg, bin_length=0, timeout=None):
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(msg[:1],flush=False)
            if len(msg)>1:
                self.instr.write(msg[1:],flush=False)
            if bin_length:
                resp=self.instr.read(bin_length)
            else:
                resp=""
            resp=resp+self.instr.readline(timeout=timeout)
            self.instr.flush_read()
        return resp
    
    
    def comm(self, op, addr=0, p1=0, p2=0, timeout=1.):
        c="C"+self._build_comm_msg(op,addr,p1,p2)
        resp=self._send_read(c,timeout=timeout)
        return self._check_response(resp)
    def query(self, op, addr=0, p1=0, p2=0, timeout=1.):
        q="Q"+self._build_comm_msg(op,addr,p1,p2)
        resp=self._send_read(q,bin_length=4,timeout=timeout)
        self._check_response(resp[4:])
        return struct.unpack("<I",resp[:4])[0]
    def upstream(self, data, timeout=1.):
        l=len(data)//4
        c="U"+struct.pack("<I",l)
        #resp=self._send_read(s,timeout=timeout)
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(c[:1],flush=False)
            self.instr.write(c[1:],flush=False)
            with self.instr.using_timeout(40.):
                self.instr.write(data,flush=False)
            resp=self.instr.readline(timeout=timeout)
            self.instr.flush_read()
        return self._check_response(resp)
    def downstream(self, length, timeout=1.):
        s="D"+struct.pack("<I",length)
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(s[:1],flush=False)
            self.instr.write(s[1:],flush=False)
            with self.instr.using_timeout(40.):
                data=self.instr.read(length*4)
            resp=self.instr.readline(timeout=timeout)
            self.instr.flush_read()
        self._check_response(resp)
        return data
    def peripheral_comm(self, dev, write_data="", read_length=0, timeout=1.):
        write_length=len(write_data)
        s="P"+struct.pack("<I",dev)+struct.pack("<I",write_length)+struct.pack("<I",read_length)
        with self.instr.single_op():
            self.instr.flush_read()
            self.instr.write(s[:1],flush=False)
            self.instr.write(s[1:],flush=False)
            if write_length:
                self.instr.write(write_data,flush=False)
            if read_length:
                with self.instr.using_timeout(40.):
                    data=self.instr.read(read_length)
            else:
                data=""
            resp=self.instr.readline(timeout=timeout)
            self.instr.flush_read()
        self._check_response(resp)
        return data
    def restart(self, full=False):
        if full:
            resp=self._send_read("R\x01")
        else:
            resp=self._send_read("R\x00")
        return self._check_response(resp)
    
    def write_ram(self, addr, value, mask=0xFFFFFFFF):
        return self.comm("write_memreg",addr,value,mask)
    def read_ram(self, addr):
        return self.query("read_memreg",addr)
    def write_ram_sfixed(self, addr, value, high, low, shift=0, mask=None):
        value=float_to_sfixed(value,high,low)
        if mask is None:
            mask=(1<<(high-low+1))-1
        self.comm("write_memreg",addr,value<<shift,mask<<shift)
        return sfixed_to_float(value,high,low)
    def read_ram_sfixed(self, addr, high, low, shift=0, mask=None):
        value=self.query("read_memreg",addr)
        if mask is None:
            mask=(1<<(high-low+1))-1
        return sfixed_to_float((value>>shift)&mask,high,low)
        
    def upstream_ram_bank(self, bank, data, start=0):
        if isinstance(data,np.ndarray):
            data=data.astype("<i4").tostring()
        l=len(data)//4
        self.comm("write_stream",bank,start,l)
        return self.upstream(data)
    def zero_ram_bank(self, bank, size, start=0):
        data="\x00"*(size*4)
        return self.upstream_ram_bank(bank,data,start=start)
    def downstream_ram_bank(self, bank, size, start=0):
        l=size//4
        self.comm("read_stream",bank,start,l)
        return self.downstream(l)
        
        
        
class FPGAController(NIOSDevice):
    _reg_map={ "DSP_mode":(0x05,2,8),
            "adc1_offset":(0x10,(15,0)),
            "adc1_scale":(0x10,(1,-14),16),
            "adc2_offset":(0x11,(15,0)),
            "adc2_scale":(0x11,(1,-14),16),
            "adc1_jitter":(0x18,(15,0)),
            "dac_offset":(0x14,(18,0)),
            "dac_scale":(0x13,(2,-15)),
            "PID_P":(0x15,(8,-15)),
            "PID_I":(0x16,(0,-23)),
            "PID_D":(0x17,(20,-3)),
            "osc_step":(0x12,),
            "pulses_period":(0x20,),
            "pulse1_end":(0x21,),
            "pulse2_start":(0x22,),
            "pulse2_end":(0x23,),

            "LEDR":(0x00,16)}
    _default_reg=(0x00,32,0)
    _reg_enums={"DSP_mode":{"gen":0,"PID":1,"transf":2}}
    @classmethod
    def _get_reg_desc(cls, reg):
        if reg in cls._reg_map:
            r=cls._reg_map[reg]
            return r+cls._default_reg[len(r):]
        else:
            raise ValueError("unrecognized register: {}".format(reg))
            
    def set_reg(self, reg, value):
        addr,size,shift=self._get_reg_desc(reg)
        if reg in self._reg_enums:
            value=self._reg_enums.get(value,value)
        if isinstance(size,tuple):
            self.write_ram_sfixed(addr,value,size[0],size[1],shift=shift)
        else:
            mask=(1<<(size+1))-1
            value=value<<shift
            self.write_ram(addr,int(value),mask)
    def get_reg(self, reg, translate_enum=True):
        addr,size,shift=self._get_reg_desc(reg)
        if isinstance(size,tuple):
            return self.read_ram_sfixed(addr,size[0],size[1],shift=shift)
        else:
            mask=(1<<(size+1))-1
            value=(self.read_ram(addr)>>shift)&mask
            if translate_enum and reg in self._reg_enums:
                pass
            return value
    __setitem__=set_reg
    __getitem__=get_reg
        
        
    def set_pulses(self, period, w1, d, w2=None):
        w2=w1 if w2 is None else w2
        self["pulses_period"]=int(period*100E6)-1
        self["pulse1_end"]=int(w1*100E6)
        self["pulse2_start"]=int(d*100E6)
        self["pulse2_end"]=int(d*100E6)+int(w2*100E6)
    
    def set_feedback_setpoint(self, setpoint):
        self["adc2_offset"]=0x8000-(0x10000/5.*setpoint)
        self["adc2_scale"]=1.
    def enable_feedback(self, enabled=True, base_level=3.):
        self["dac_offset"]=(1<<17)/20.*base_level
        self["dac_scale"]=1. if enabled else 0.
    def teach_feedback(self, delay=10., reset=True):
        if reset:
            self.write_ram(0x05,0x01,0x01)
            self.zero_ram_bank(0x10,0x1000)
            self.write_ram(0x05,0x00,0x01)
        self["PID_I"]=-5E-3
        time.sleep(delay)
        self["PID_I"]=0
        
        

    def W5500_read(self, block, addr, l):
        comm=struct.pack(">H",addr)+struct.pack("B",(block<<3)&0xFF)
        return self.peripheral_comm(0x0110,comm,l)
    def W5500_write(self, block, addr, data, readback=True):
        comm=struct.pack(">H",addr)+struct.pack("B",((block<<3)&0xFF)|0x04)+data
        self.peripheral_comm(0x0110,comm)
        return self.W5500_read(block,addr,len(data)) if readback else ""