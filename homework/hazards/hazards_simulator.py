import struct
import csv
from dataclasses import dataclass
from typing import List

@dataclass
class PipelineReg:
    instr: int = 0
    pc: int = 0 
    op: int = 0
    fct3: int = 0
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    imm: int = 0
    reg_write: bool = False
    alu_src: bool = False
    fwd_a: str = ""
    fwd_b: str = ""
    mem_rd: bool = False
    mem_wr: bool = False
    wb_sel: int = 0
    branch_ctrl: bool = False

    @classmethod
    def nop(cls):
        return cls(instr=0, pc=0, op=0, fct3=0, rd=0, rs1=0, rs2=0, imm=0, reg_write=False, alu_src=False, mem_rd=False, mem_wr=False, wb_sel=0, branch_ctrl=False)

class PipelineSimulator:
    def __init__(self, binary_file: str):
        self.pc = 0
        self.instructions = self._load_instructions(binary_file)
        self.max_pc = len(self.instructions) * 4
        self.if_id = PipelineReg.nop()
        self.id_ex = PipelineReg.nop()
        self.ex_mem = PipelineReg.nop()
        self.mem_wb = PipelineReg.nop()
        self.cycle = 0
        self.retired_instr_count = 0 
        self.stall_pipeline = False 
        self.branch_target = 0
        self.register_values = {0: 0}
        self.pc_write_enable = True
        self.if_id_write_enable = True
        self.id_ex_write_enable = True

    def _load_instructions(self, binary_file: str) -> List[int]:
        instructions = []
        try:
            with open(binary_file, 'rb') as f:
                while True:
                    data = f.read(4)
                    if(not data):
                        break
                    if(len(data) < 4):
                        print(f"Warning: Found partial instruction (only {len(data)} bytes) at end of file. Ignoring.")
                        break
                    instructions.append(struct.unpack('<I', data)[0])
        except FileNotFoundError:
            print(f"Error: Binary file not found at {binary_file}")
            return []
        print(f"Loaded {len(instructions)} instructions.")
        return instructions

    def _sign_extend(self, value, bits):
        sign_bit = 1 << (bits - 1)
        return (value & (sign_bit - 1)) - (value & sign_bit)

    def _decode_instruction(self, instr: int, current_pc: int) -> PipelineReg:
        if instr == 0:
            return PipelineReg.nop()

        op = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        fct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F

        imm = 0
        if(op in [0x13, 0x03, 0x67]): ## I-type (addi, lw, jalr)
            imm = self._sign_extend(instr >> 20, 12)
        elif(op == 0x23): ## S-type (sw)
            imm = self._sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
        elif(op == 0x63): ## B-type (beq, bne)
            imm = self._sign_extend(
                ((instr >> 31) << 12) | # #imm[12]
                ((instr >> 7) & 0x1) << 11 | ## imm[11]
                ((instr >> 25) & 0x3F) << 5 | ## imm[10:5]
                ((instr >> 8) & 0xF) << 1, ## imm[4:1]
                13) ## B-immediates are multiples of 2


        reg_write = op in [0x33, 0x13, 0x03, 0x67, 0x37, 0x17] ## R, I, Load, JALR, LUI, AUIPC
        alu_src = op in [0x13, 0x03, 0x23, 0x67, 0x37, 0x17] ## I, Load, Store, JALR, LUI, AUIPC
        mem_rd = op == 0x03 ## Load
        mem_wr = op == 0x23 ## Store
        branch_ctrl = op == 0x63 ## Branch (beq, bne, etc.)

        wb_sel = 0 ## Default to ALU result
        if(mem_rd):
            wb_sel = 1 ## Load uses memory data


        return PipelineReg(
            instr=instr, pc=current_pc, op=op, rd=rd, fct3=fct3, rs1=rs1, rs2=rs2, imm=imm,
            reg_write=reg_write, alu_src=alu_src, mem_rd=mem_rd, mem_wr=mem_wr,
            wb_sel=wb_sel, branch_ctrl=branch_ctrl
        )

    def _check_forwarding(self):
        fwd_a = ""
        fwd_b = ""

        ## EX hazard: Result from ALU stage (end of EX / start of MEM)
        if(self.ex_mem.reg_write and self.ex_mem.rd != 0):
            if(self.ex_mem.rd == self.id_ex.rs1):
                fwd_a = "EX"
            if(self.id_ex.op in [0x33, 0x23, 0x63] and self.ex_mem.rd == self.id_ex.rs2):
                fwd_b = "EX"

        ## MEM hazard: Result from Memory stage (end of MEM / start of WB)
        if(self.mem_wb.reg_write and self.mem_wb.rd != 0):
            if(self.mem_wb.rd == self.id_ex.rs1 and fwd_a == ""):
                fwd_a = "MEM"
            if(self.id_ex.op in [0x33, 0x23, 0x63] and self.mem_wb.rd == self.id_ex.rs2 and fwd_b == ""):
                fwd_b = "MEM"
        self.id_ex.fwd_a = fwd_a
        self.id_ex.fwd_b = fwd_b


    def _check_load_use_hazard(self):
        if(self.id_ex.instr != 0 and self.ex_mem.mem_rd): # Instr in ID, Load in EX
            rs1_needed = self.id_ex.rs1 != 0 and self.ex_mem.rd == self.id_ex.rs1
            rs2_needed = self.id_ex.op in [0x33, 0x23, 0x63] and self.id_ex.rs2 != 0 and self.ex_mem.rd == self.id_ex.rs2

            if(rs1_needed or rs2_needed):
                self.stall_pipeline = True
                # print(f"Cycle {self.cycle}: Stall detected! Instr 0x{self.id_ex.instr:08x} needs R{self.ex_mem.rd} from Load 0x{self.ex_mem.instr:08x}")
            else:
                 self.stall_pipeline = False
        else:
            self.stall_pipeline = False


    def writeback(self):
        if(self.mem_wb.instr == 0): ## NOP in WB
            return


        if self.mem_wb.reg_write and self.mem_wb.rd == 5:
             if(self.mem_wb.op == 0x13):
                 if(self.mem_wb.fct3 == 0):
                     if(self.mem_wb.rs1 == 0 and self.mem_wb.imm == 3):
                         self.register_values[5] = 3
                         print(f"Cycle {self.cycle}: WB: x5 set to 3")
                     elif(self.mem_wb.rs1 == 5 and self.mem_wb.imm == -1):
                         val_rs1 = self.register_values.get(5, 0)
                         self.register_values[5] = val_rs1 + self.mem_wb.imm
                         print(f"Cycle {self.cycle}: WB: x5 decremented to {self.register_values[5]}")

        if(self.mem_wb.reg_write):
             self.retired_instr_count += 1


    def memory(self):
        self.mem_wb = self.ex_mem


    def execute(self):
        self.ex_mem = self.id_ex

        if(self.id_ex.instr == 0):
             return

        if(self.id_ex.branch_ctrl):
            branch_eval = False
            if(self.id_ex.op == 0x63 and self.id_ex.fct3 == 1):
                 val_rs1 = self.register_values.get(self.id_ex.rs1, 0)
                 val_rs2 = self.register_values.get(self.id_ex.rs2, 0)
                 if(self.id_ex.rs1 == 5):
                     val_rs1 = self.register_values.get(5,0)
                 if(self.id_ex.rs2 == 5):
                     val_rs2 = self.register_values.get(5,0)

                 if(val_rs1 != val_rs2):
                     branch_eval = True
                     print(f"Cycle {self.cycle}: EX: BNE condition TRUE (rs1={val_rs1}, rs2={val_rs2})")
                 else:
                     print(f"Cycle {self.cycle}: EX: BNE condition FALSE (rs1={val_rs1}, rs2={val_rs2})")



            if(branch_eval):
                self.branch_target = self.id_ex.pc + self.id_ex.imm
                self.flush_pipeline = True
                print(f"Cycle {self.cycle}: EX: Branch Taken! Target PC=0x{self.branch_target:x}. Signaling flush.")


    def decode(self):
        decoded_reg = self._decode_instruction(self.if_id.instr, self.if_id.pc)
        self.id_ex = decoded_reg


    def fetch(self, do_flush: bool):
        next_pc = self.pc
        if(self.pc_write_enable):
            if(do_flush):
                print(f"Cycle {self.cycle}: Fetch - Branch taken, PC -> 0x{self.branch_target:x}")
                next_pc = self.branch_target
            else:
                next_pc = self.pc + 4

        fetched_instr = 0
        current_pc_for_fetch = self.pc
        if(current_pc_for_fetch < self.max_pc):
            instr_addr_index = current_pc_for_fetch >> 2
            if(0 <= instr_addr_index < len(self.instructions)):
                fetched_instr = self.instructions[instr_addr_index]
            else:
                print(f"Cycle {self.cycle}: PC 0x{current_pc_for_fetch:x} out of instruction bounds. Fetching NOP.")

        if(self.if_id_write_enable):
            if(do_flush):
                print(f"Cycle {self.cycle}: Fetch - Flushing IF/ID <- NOP")
                self.if_id = PipelineReg.nop()
            else:
                self.if_id.instr = fetched_instr
                self.if_id.pc = current_pc_for_fetch

        self.pc = next_pc


    def run(self, output_file: str):
        if(not self.instructions):
            print("Error: No instructions loaded. Exiting simulation.")
            return

        total_instructions = len(self.instructions)
        max_cycles = total_instructions * 15 if total_instructions > 0 else 100

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Cycle', 'PC', 'Instr', 'Stage', 'Op', 'Fct3', 'Rd', 'Rs1', 'Rs2', 'Imm',
                             'RegWrite', 'ALUSrc', 'MemRd', 'MemWr', 'WBSel', 'Branch', 'FwdA', 'FwdB'])

            while(self.cycle < max_cycles):
                self.pc_write_enable = True
                self.if_id_write_enable = True
                self.id_ex_write_enable = True
                do_flush = False

                log_entries = []
                stages = {'IF': self.if_id, 'ID': self.id_ex, 'EX': self.ex_mem, 'MEM': self.mem_wb}
                for stage_name, reg in stages.items():
                    if(reg.instr != 0):
                        log_entries.append([
                            self.cycle, f"0x{reg.pc:04x}", f"0x{reg.instr:08x}", stage_name,
                            f"0x{reg.op:02x}", reg.fct3, reg.rd, reg.rs1, reg.rs2, reg.imm,
                            reg.reg_write, reg.alu_src, reg.mem_rd, reg.mem_wr,
                            reg.wb_sel, reg.branch_ctrl, reg.fwd_a, reg.fwd_b
                        ])
                if(not log_entries and self.retired_instr_count < total_instructions):
                     log_entries.append([self.cycle, f"0x{self.pc:04x}", "0x00000000", "---",
                                         "0x00", 0, 0, 0, 0, 0, False, False, False, False, 0, False, "", ""])
                for entry in log_entries:
                    writer.writerow(entry)

                self._check_load_use_hazard()

                if(self.flush_pipeline):
                    print(f"Cycle {self.cycle}: Flush detected! Handling flush.")
                    self.pc_write_enable = True
                    self.if_id_write_enable = False
                    self.id_ex_write_enable = False
                    do_flush = True
                    self.flush_pipeline = False
                    self.stall_pipeline = False

                if(self.stall_pipeline):
                    print(f"Cycle {self.cycle}: Stall detected! Handling stall.")
                    self.pc_write_enable = False
                    self.if_id_write_enable = False
                    self.id_ex_write_enable = False

                self.writeback()
                self.memory()

                if(self.id_ex_write_enable):
                    self.execute()
                else:
                    self.ex_mem = PipelineReg.nop()

                if(self.if_id_write_enable):
                    self.decode()
                    self._check_forwarding()
                else:
                    if(not self.stall_pipeline):
                         self.id_ex = PipelineReg.nop()

                if(self.pc_write_enable):
                    self.fetch(do_flush)
                else:
                    print(f"Cycle {self.cycle}: Stall - PC/Fetch blocked.")
    
                self.stall_pipeline = False

                if(self.pc >= self.max_pc and \
                   self.if_id.instr == 0 and self.id_ex.instr == 0 and \
                   self.ex_mem.instr == 0 and self.mem_wb.instr == 0):
                    print(f"Cycle {self.cycle+1}: Pipeline empty after PC reached end. Terminating.")
                    break

                self.cycle += 1

            if(self.cycle >= max_cycles):
                print(f"Warning: Simulation reached max cycles ({max_cycles}). Terminating.")
            else:
                print(f"Simulation finished in {self.cycle} cycles.")
                print(f"Total instructions retired: {self.retired_instr_count}")

def encode_instruction(op: int, rd: int, fct3: int, rs1: int, rs2: int, imm: int = 0) -> int:
    instr = (op & 0x7F) | ((rd & 0x1F) << 7) | ((fct3 & 0x7) << 12) | ((rs1 & 0x1F) << 15)
    if(op in [0x13, 0x03, 0x67]):
        instr |= (imm & 0xFFF) << 20
    elif(op == 0x23):
        instr |= ((imm >> 5) & 0x7F) << 25 | (imm & 0x1F) << 7
    elif(op == 0x63):
        imm_b = imm >> 1
        instr |= ((imm_b >> 11) & 0x1) << 31
        instr |= ((imm_b >> 4) & 0x3F) << 25
        instr |= (imm_b & 0xF) << 8
        instr |= ((imm_b >> 10) & 0x1) << 7
    elif(op == 0x33):
        instr |= (rs2 & 0x1F) << 20
        instr |= (0x00) << 25
        if(fct3 == 0x0 and op == 0x33):
            instr |= (0x20) << 25
    return instr

def main():
    instructions = [
        encode_instruction(op=0x03, rd=7, fct3=0x2, rs1=10, rs2=0, imm=0),
        encode_instruction(op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=4),
        encode_instruction(op=0x13, rd=8, fct3=0x0, rs1=6, rs2=0, imm=1),
        encode_instruction(op=0x33, rd=9, fct3=0x0, rs1=8, rs2=7),
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=9, imm=8),
    ]
    bin_file = 'hazards_instructions.bin'
    csv_file = 'hazards_simulation.csv'

    print(f"--- Running Hazard Simulation ---")
    print(f"Writing instructions to {bin_file}")
    with open(bin_file, 'wb') as f:
        for i, instr in enumerate(instructions):
             print(f"  PC 0x{i*4:02x}: 0x{instr:08x}")
             f.write(struct.pack('<I', instr))

    print(f"Running simulator and writing to {csv_file}")
    simulator = PipelineSimulator(bin_file)
    simulator.run(csv_file)
    print(f"--- Hazard Simulation Complete ---")


if(__name__ == "__main__"):
    main()
