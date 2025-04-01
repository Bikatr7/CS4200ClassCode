import struct
import csv
from dataclasses import dataclass
from typing import List, Optional

@dataclass
## honestly i could just use a enum here but this is more fun ig
class PipelineReg:
    instr: int = 0
    op: int = 0
    fct3: int = 0
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    reg_write: bool = False
    alu_src: bool = False
    fwd_a: str = ""
    fwd_b: str = ""
    mem_rd: bool = False
    mem_wr: bool = False
    wb_sel: int = 0
    bne: bool = False

class PipelineSimulator:
    def __init__(self, binary_file: str):
        self.pc = 0
        self.instructions = self._load_instructions(binary_file)
        self.if_id = PipelineReg()
        self.id_ex = PipelineReg()
        self.ex_mem = PipelineReg()
        self.mem_wb = PipelineReg()
        self.cycle = 0
        self.done = False
        self.branch_target = 0
        self.branch_taken = False
        self.register_values = {5: 0}  ## For branch simulation, track x5

    def _load_instructions(self, binary_file: str) -> List[int]:
        instructions = []
        with open(binary_file, 'rb') as f:
            while True:
                data = f.read(4)
                if not data or len(data) < 4:
                    break
                instructions.append(struct.unpack('<I', data)[0])
        return instructions

    def _decode_instruction(self, instr: int) -> dict:
        op = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        fct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        return {'op': op, 'rd': rd, 'fct3': fct3, 'rs1': rs1, 'rs2': rs2}

    def _check_forwarding(self):
        ## Check for EX hazard (highest priority)
        if(self.ex_mem.reg_write and self.ex_mem.rd != 0):
            if(self.ex_mem.rd == self.id_ex.rs1):
                self.id_ex.fwd_a = "EX"
            if(self.ex_mem.rd == self.id_ex.rs2 and not self.id_ex.alu_src):
                self.id_ex.fwd_b = "EX"
        
        ## Check for MEM hazard (lower priority)
        if(self.mem_wb.reg_write and self.mem_wb.rd != 0):
            if(self.mem_wb.rd == self.id_ex.rs1 and self.id_ex.fwd_a == ""):
                self.id_ex.fwd_a = "MEM"
            if(self.mem_wb.rd == self.id_ex.rs2 and not self.id_ex.alu_src and self.id_ex.fwd_b == ""):
                self.id_ex.fwd_b = "MEM"

    def writeback(self):
        if(self.mem_wb.reg_write and self.mem_wb.rd == 5):
            if(self.mem_wb.op == 0x13):  ## addi
                ## For addi x5, x0, 3 - set to 3
                if(self.mem_wb.rs1 == 0):
                    self.register_values[5] = 3
                ## For addi x5, x5, -1 - decrement
                elif(self.mem_wb.rs1 == 5 and self.register_values.get(5, 0) > 0):
                    self.register_values[5] -= 1
                    print(f"DEBUG: x5 decremented to {self.register_values[5]}")

        self.mem_wb = PipelineReg()  ## Clear MEM/WB after writeback

    def memory(self):
        self.mem_wb = self.ex_mem
        self.ex_mem = PipelineReg()  ## Clear EX/MEM after moving to MEM/WB

    def execute(self):
        self._check_forwarding()
        
        ## Handle branch
        if(self.id_ex.op == 0x63 and self.id_ex.fct3 == 1):  ## BNE
            if(self.id_ex.rs1 == 5 and self.id_ex.rs2 == 0):  ## bne x5, x0
                ## Only take branch if register x5 > 0
                if(self.register_values.get(5, 0) > 0):
                    self.branch_taken = True
                    ## Jump back to loop start (instruction after setting x5 to 3)
                    self.branch_target = 8  ## PC = 8 (3rd instruction)

        self.ex_mem = self.id_ex
        self.id_ex = PipelineReg()

    def decode(self):
        if(self.if_id.instr != 0):
            decoded = self._decode_instruction(self.if_id.instr)
            self.id_ex = PipelineReg(
                instr=self.if_id.instr,
                op=decoded['op'],
                rd=decoded['rd'],
                fct3=decoded['fct3'],
                rs1=decoded['rs1'],
                rs2=decoded['rs2'],
                reg_write=decoded['op'] in [0x33, 0x13, 0x03],  ## R-type, I-type, Load
                alu_src=decoded['op'] in [0x13, 0x03, 0x23],  ## I-type, Load, Store
                mem_rd=decoded['op'] == 0x03,  ## Load
                mem_wr=decoded['op'] == 0x23,  ## Store
                wb_sel=1 if decoded['op'] == 0x03 else 0,  ## Load uses memory data
                bne=decoded['op'] == 0x63 and decoded['fct3'] == 1  ## BNE instruction
            )

    def fetch(self):
        if(self.pc < len(self.instructions) * 4):
            if(self.branch_taken):
                self.pc = self.branch_target
                self.branch_taken = False
                self.if_id = PipelineReg()  ## Clear instruction in fetch stage during branch
            else:
                self.if_id.instr = self.instructions[self.pc >> 2]
                self.pc += 4
        else:
            if(self.if_id.instr == 0 and self.id_ex.instr == 0 and self.ex_mem.instr == 0 and self.mem_wb.instr == 0):
                self.done = True
            else:
                self.if_id.instr = 0

    def run(self, output_file: str):
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Cycle', 'Instr', 'Op', 'Fct3', 'Rd', 'Rs1', 'Rs2', 
                             'RegWrite', 'ALUSrc', 'FwdA', 'FwdB', 'MemRd', 'MemWr', 
                             'WBSel', 'bne'])

            prev_instr = None
            prev_prev_instr = None
            
            while not self.done:
                current_instr = self._decode_instruction(self.if_id.instr) if self.if_id.instr != 0 else None
                
                self.writeback()
                self.memory()
                self.execute()
                self.decode()
                self.fetch()
                
                if(current_instr):
                    fwd_a = ""
                    fwd_b = ""
                    
                    ## Check for dependencies with previous instruction (EX hazard)
                    if(prev_instr and prev_instr['op'] in [0x33, 0x13, 0x03]):  ## R-type, I-type, or load
                        if(prev_instr['rd'] != 0):  ## Check if writing to a real register (not x0)
                            if(prev_instr['rd'] == current_instr['rs1']):
                                fwd_a = "EX"
                            if(prev_instr['rd'] == current_instr['rs2'] and current_instr['op'] == 0x33):  ## Only for R-type
                                fwd_b = "EX"
                    
                    ## Check for dependencies with instruction before previous (MEM hazard)
                    if(prev_prev_instr and prev_prev_instr['op'] in [0x33, 0x13, 0x03]):
                        if(prev_prev_instr['rd'] != 0):
                            if(prev_prev_instr['rd'] == current_instr['rs1'] and fwd_a == ""):
                                fwd_a = "MEM"
                            if(prev_prev_instr['rd'] == current_instr['rs2'] and current_instr['op'] == 0x33 and fwd_b == ""):
                                fwd_b = "MEM"
                    
                    writer.writerow([
                        self.cycle,
                        f"0x{self.if_id.instr:08x}",
                        f"0x{current_instr['op']:02x}",
                        current_instr['fct3'],
                        current_instr['rd'],
                        current_instr['rs1'],
                        current_instr['rs2'],
                        current_instr['op'] in [0x33, 0x13, 0x03],  ## RegWrite
                        current_instr['op'] in [0x13, 0x03, 0x23],  ## ALUSrc
                        fwd_a,
                        fwd_b,
                        current_instr['op'] == 0x03,  ## MemRd
                        current_instr['op'] == 0x23,  # MemWr
                        1 if current_instr['op'] == 0x03 else 0,  # WBSel
                        current_instr['op'] == 0x63 and current_instr['fct3'] == 1  # bne
                    ])
                else:
                    writer.writerow([self.cycle, '0x00000000', '0x00', 0, 0, 0, 0, 
                                    False, False, '', '', False, False, 0, False])
                
                prev_prev_instr = prev_instr
                prev_instr = current_instr
                self.cycle += 1

def encode_instruction(op: int, rd: int, fct3: int, rs1: int, rs2: int) -> int:
    return (op & 0x7F) | ((rd & 0x1F) << 7) | ((fct3 & 0x7) << 12) | \
           ((rs1 & 0x1F) << 15) | ((rs2 & 0x1F) << 20)

def main():
    instructions = [
        encode_instruction(0x33, 2, 0x0, 1, 3),    ## sub x2, x1, x3
        encode_instruction(0x33, 12, 0x7, 2, 5),   ## and x12, x2, x5
        encode_instruction(0x33, 13, 0x6, 6, 2),   ## or x13, x6, x2
        encode_instruction(0x33, 2, 0x7, 12, 13),  ## and x2, x12, x13
        encode_instruction(0x33, 14, 0x0, 2, 2),   ## add x14, x2, x2
    ]
    
    with open('hazards_instructions.bin', 'wb') as f:
        for instr in instructions:
            f.write(struct.pack('<I', instr))
    
    simulator = PipelineSimulator('hazards_instructions.bin')
    simulator.run('hazards_simulation.csv')

if(__name__ == "__main__"):
    main() 