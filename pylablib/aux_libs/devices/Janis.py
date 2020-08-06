"""
Janis Jacob controller (custom hardware, probably not applicable to other devices).
"""

import socket
import struct
import collections
import contextlib

import numpy as np

class JacobServer(object):
    def __init__(self, addr="10.10.1.17", port=5557, single_use_socket=False):
        object.__init__(self)
        self.addr=addr
        self.port=port
        self._single_use_socket=single_use_socket
        self.sock=None
        
    def close(self):
        if self.sock:
            self.sock.close()
    
    def _build_socket(self):
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((self.addr,self.port))
        s.settimeout(10.)
        return s
    def _close_socket(self):
        if self._single_use_socket and self.sock:
            self.sock.close()
            self.sock=None
    @contextlib.contextmanager
    def _using_socket(self):
        self.sock=self.sock or self._build_socket()
        try:
            yield
        finally:
            self._close_socket()
    @staticmethod
    def _send_msg(s, msg):
        msg=struct.pack(">i4",len(msg))+msg
        sent_total=0
        while sent_total<len(msg):
            sent=s.send(msg[sent_total:])
            if sent==0:
                raise RuntimeError("broken connection")
            sent_total=sent_total+sent
    @staticmethod
    def _recv_fixedlen(s, l):
        buf=""
        while len(buf)<l:
            recvd=s.recv(l-len(buf))
            if len(recvd)==0:
                raise RuntimeError("broken connection")
            buf=buf+recvd
        return buf
    @staticmethod
    def _recv_msg(s):
        msg_len=JacobServer._recv_fixedlen(s,4)
        msg_len,=struct.unpack(">i4",msg_len)
        return JacobServer._recv_fixedlen(s,msg_len)
    @staticmethod
    def _flush(s, timeout=0.1):
        to=s.gettimeout()
        s.settimeout(timeout)
        l=0
        try:
            while True:
                recvd=s.recv(1)
                if len(recvd)==0:
                    raise RuntimeError("broken connection")
                l=l+len(recvd)
        except socket.timeout:
            return l
        finally:
            s.settimeout(to)
        
    def comm(self, comm):
        with self._using_socket():
            self._send_msg(self.sock,comm)
    def query(self, query):
        with self._using_socket():
            self._send_msg(self.sock,query)
            return self._recv_msg(self.sock)
    def flush(self, timeout=0.1):
        with self._using_socket():
            return self._flush(self.sock,timeout=timeout)
    
    
    StatusSimple=collections.namedtuple("StatusSimple",["ain","aout","dout"])
    @staticmethod
    def _parse_status(status):
        ain=np.fromstring(status[12:12+16*8],">f8")
        aout=np.array(list(np.fromstring(status[224:224+8],">f8"))+[0.]*3)
        dout_int,=struct.unpack("<i4",status[4:8])
        dout="{:032b}".format(dout_int)[::-1]
        dout=[c=="1" for c in dout]
        return JacobServer.StatusSimple(ain,aout,dout)
    def get_status_simple(self):
        status=self.query("GetStatus")
        return self._parse_status(status)
    
    StatusDecoded=collections.namedtuple("StatusDecoded",["pressures","flow","valves","V5","pumps","pump_status"])
    @staticmethod
    def _get_pressure_mbar(voltage):
        return 10**(-5.5+voltage)
    @staticmethod
    def _get_flow_umoles(voltage):
        return voltage*200.
    @staticmethod
    def _voltage_to_percentage_open(voltage):
        return voltage*20.
    @staticmethod
    def _percentage_open_to_voltage(perc):
        return perc/20.
    @staticmethod
    def _decode_status(status):
        ain=status.ain
        pressures=[JacobServer._get_pressure_mbar(v) for v in ain[[0,1,2,4]]]
        flow=JacobServer._get_flow_umoles(ain[3])
        V5=JacobServer._voltage_to_percentage_open(status.aout[0])
        dout=status.dout
        valves=[dout[25],not dout[0],dout[1],not dout[2],bool(V5)]+dout[3:16] # V1 to V22, skipping V16 to V19
        pumps=[dout[27],dout[26],dout[28]] # main, booster, compressor
        pump_status=[ain[8]<1., ain[9]>1., ain[10]>1., ain[11]<1., ain[12]<1., ain[13]<1.] # pump running, pump warning, pump hazard, pump N2 flow, pump FV interlock, water flow
        return JacobServer.StatusDecoded(pressures,flow,valves,V5,pumps,pump_status)
    def get_status_decoded(self):
        return self._decode_status(self.get_status_simple())
    s=get_status_decoded    
    
    @staticmethod
    def _num_to_hex(x):
        bs=[(x>>(8*n))&0xFF for n in range(4)] # convert into bytes, LSB first
        return "".join(["{:02x}".format(b) for b in bs])
    def setDO(self, channel, state):
        mask=self._num_to_hex(1<<channel)
        value=mask if state else "0"*8
        self.comm("SetDO={},{}".format(mask,value))
        self.flush(3.)
    def setDO_multiple(self, state, mask):
        state=self._num_to_hex(state)
        mask=self._num_to_hex(mask)
        self.comm("SetDO={},{}".format(mask,state))
        self.flush(3.)
    def setAO(self, channel, value):
        if channel!=0:
            raise ValueError("can only set value in channel 0")
        self.comm("SetAO=0,{:.4f} 00".format(value))
        self.flush(3.)
        
    def switch_pump(self, pump, state):
        pump_msg="PumpOn" if state else "PumpOff"
        if pump=="main":
            self.comm("{}={}".format(pump_msg,8))
            self.flush(3.)
        elif pump=="booster":
            self.comm("{}={}".format(pump_msg,4))
            self.flush(3.)
        elif pump=="compressor":
            self.setDO(28,state)
        else:
            raise ValueError("unrecognized pump name: {}".format(pump))
    def _get_valve_channel(self, valve):
        if valve==5:
            return None
        else:
            if valve==1:
                return 25
            elif valve<=4:
                return valve-2
            elif valve<=15:
                return valve-3
            else:
                return valve-7
    def switch_valve(self, valve, state):
        if valve==5:
            self.setAO(0,self._percentage_open_to_voltage(float(state)))
        else:
            if valve in {2,4}:
                state=not state
            channel=self._get_valve_channel(valve)
            self.setDO(channel,state)
    def switch_multiple_valves(self, valves_on=None, valves_off=None, V5=None):
        if V5 is not None:
            self.switch_valve(5,V5)
        valves_on=valves_on or []
        valves_off=valves_off or []
        state=0
        mask=0
        for v in valves_on+valves_off:
            mask=mask|(1<<(self._get_valve_channel(v)))
        for v in valves_on:
            if v not in {2,4}:
                state=state|(1<<(self._get_valve_channel(v)))
        for v in valves_off:
            if v in {2,4}:
                state=state|(1<<(self._get_valve_channel(v)))
        self.setDO_multiple(state,mask)