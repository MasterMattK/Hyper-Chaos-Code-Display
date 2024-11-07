from struct import pack, unpack
from multiprocessing import shared_memory
import psutil
from enum import Enum

"""
MIT License

Copyright (c) 2017 aldelaro5

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

class Dolphin(object):
    MEM_START = 0x80000000
    MEM_END = 0x81800000

    class ReturnFlags(Enum):
        SUCCESS = 1
        NO_DOLPHIN = 2
        DOLPHIN_TAKEN = 3
        SHM_FAIL = 4

    def __init__(self):
        self.pid = -1
        self.dolphinMemory = None 
        self.processMemory = None
        
    def reset(self):
        self.pid = -1
        self.dolphinMemory = None 
        self.processMemory = None
        
    def find_other_hooks(self):
        skip_pids=[]
        name = psutil.Process().name()
        for proc in psutil.process_iter():
            if proc.name() == name and proc.pid != psutil.Process().pid:
                flag = self.init_shared_memory('smso.'+str(proc.pid))
                if flag != self.ReturnFlags.SUCCESS:
                    return skip_pids, flag
                taken_pid = unpack(">I", self.read_ram(0, 4))[0]
                print(taken_pid)
                skip_pids.append(taken_pid)

        return skip_pids, self.ReturnFlags.SUCCESS
                
                
    def find_dolphin(self, skip_pids=[]) -> ReturnFlags:
        for proc in psutil.process_iter():
            if proc.pid not in skip_pids and proc.name() in ("Dolphin.exe", "DolphinQt2.exe", "DolphinWx.exe"):
                self.pid = proc.pid
                break

        if self.pid == -1:
            return self.ReturnFlags.NO_DOLPHIN 
        
        return self.ReturnFlags.SUCCESS
    
    def init_shared_memory(self, shm_name, size=None):
        if size == None:
            if self.dolphinMemory != None:
                self.dolphinMemory.close()
                self.dolphinMemory = None
            try:
                self.dolphinMemory = shared_memory.SharedMemory(shm_name)
                return self.ReturnFlags.SUCCESS
            except FileNotFoundError:
                self.dolphinMemory = None
                return self.ReturnFlags.SHM_FAIL
        else:
            if self.processMemory != None:
                self.processMemory.close()
                self.processMemory = None
            try:
                self.processMemory = shared_memory.SharedMemory(create=True, name=shm_name, size=size)
                return self.ReturnFlags.SUCCESS
            except FileNotFoundError:
                self.processMemory = None
                return self.ReturnFlags.SHM_FAIL

    def hook_dolphin(self):
        skip_pids, flag = self.find_other_hooks()
        if flag != self.ReturnFlags.SUCCESS:
            return flag
        flag = self.find_dolphin(skip_pids)
        if flag != self.ReturnFlags.SUCCESS:
            return flag
        flag = self.init_shared_memory('dolphin-emu.'+str(self.pid))
        if flag != self.ReturnFlags.SUCCESS:
            return flag
        flag = self.init_shared_memory('smso.'+str(psutil.Process().pid), 16)
        if flag != self.ReturnFlags.SUCCESS:
            return flag
        self.processMemory.buf[0:4] = pack(">I", self.pid)
        psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        #psutil.Process().ionice(psutil.IOPRIO_HIGH)
        return self.ReturnFlags.SUCCESS

    # these are the underlying read and write functions that get called by all other reads and writes
    def read_ram(self, offset, size):
        return self.dolphinMemory.buf[offset:offset+size]
    def write_ram(self, offset, data):
        self.dolphinMemory.buf[offset:offset+len(data)] = data

    # the rest of the functions are the specific read and write calls. I have them all as separate
    # calls to prevent any sort of mistakes with passing in incorrect data types. 
    # It also helps with readability in general.
    def read_u8(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 1)
        return unpack(">B", value)[0]
    def read_u16(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 2)
        return unpack(">H", value)[0]
    def read_u32(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 4)
        return unpack(">I", value)[0]
    def read_u64(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 8)
        return unpack(">Q", value)[0]

    def read_s8(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 1)
        return unpack(">b", value)[0]
    def read_s16(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 2)
        return unpack(">h", value)[0]
    def read_s32(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 4)
        return unpack(">i", value)[0]
    def read_s64(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr-0x80000000, 8)
        return unpack(">q", value)[0]

    def read_f32(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr - 0x80000000, 4)
        return unpack(">f", value)[0]
    def read_f64(self, addr):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        value = self.read_ram(addr - 0x80000000, 8)
        return unpack(">d", value)[0]
    
    # be super careful using this function as it doesn't do much error checking.
    # possible errors could arise from invalid pointers or invalid strings in general
    def read_string_ptr(self, addr_ptr: int, limit: int=50) -> str:
        if addr_ptr < self.MEM_START or addr_ptr > self.MEM_END:
            return ""

        addr = self.read_u32(addr_ptr)

        data = bytearray()
        count = 0
        while count < limit:
            char = self.read_u8(addr)
            if char == 0:
                break
            data.append(char)
            addr += 1
            count += 1
        try:
            return data.decode('shift-jis')
        except UnicodeDecodeError:
            return ""
        
    # be super careful using this function as it doesn't do much error checking.
    # possible errors could arise from invalid pointers or invalid strings in general
    def read_string(self, addr: int, limit: int=50) -> str:
        if addr < self.MEM_START or addr > self.MEM_END:
            return ""

        data = bytearray()
        count = 0
        while count < limit:
            char = self.read_u8(addr)
            if char == 0:
                break
            data.append(char)
            addr += 1
            count += 1
        try:
            return data.decode('shift-jis')
        except UnicodeDecodeError:
            return ""


    def write_u8(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">B", val))
    def write_u16(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">H", val))
    def write_u32(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">I", val))
    def write_u64(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">Q", val))

    def write_s8(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">b", val))
    def write_s16(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">h", val))
    def write_s32(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">i", val))
    def write_s64(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">q", val))

    def write_f32(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">f", val))
    def write_f64(self, addr, val):
        if addr < self.MEM_START or addr > self.MEM_END:
            return 0
        return self.write_ram(addr - 0x80000000, pack(">d", val))

        
if __name__ == "__main__":
    dolphin = Dolphin()
    import multiprocessing 
    
    if dolphin.find_dolphin():

        print("Found Dolphin!")
    else:
        print("Didn't find Dolphin")

    print(dolphin.pid)
    
    dolphin.init_shared_memory()
    if dolphin.init_shared_memory():
        print("We found MEM1 and/or MEM2!")
    else:
        print("We didn't find it...")
    
    import random 
    randint = random.randint
    from timeit import default_timer
    
    start = default_timer()
    
    print("Testing Shared Memory Method")
    start = default_timer()
    count = 500000
    for i in range(count):
        value = randint(0, 2**32-1)
        dolphin.write_u32(0x80000000, value)
        
        result = dolphin.read_u32(0x80000000)
        assert result == value
    diff = default_timer()-start 
    print(count/diff, "per sec")
    print("time: ", diff)
    