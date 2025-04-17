import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    ## Instruction sequence with a loop controlled by x5
    ## PC     Instruction       Encoding Args
    ## 0x00:  lw x7, 0(x10)     op=0x03, rd=7, fct3=0x2, rs1=10, rs2=0, imm=0
    ## 0x04:  addi x5, x0, 3    op=0x13, rd=5, fct3=0x0, rs1=0, rs2=0, imm=3
    ## 0x08:  lw x6, 0(x7)      op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=0   <- Loop Start (Target PC)
    ## 0x0C:  addi x6, x6, 1    op=0x13, rd=6, fct3=0x0, rs1=6, rs2=0, imm=1
    ## 0x10:  sw x6, 0(x7)      op=0x23, rd=0, fct3=0x2, rs1=7, rs2=6, imm=0
    ## 0x14:  addi x7, x7, 4    op=0x13, rd=7, fct3=0x0, rs1=7, rs2=0, imm=4
    # 0x18:  addi x5, x5, -1   op=0x13, rd=5, fct3=0x0, rs1=5, rs2=0, imm=-1
    ## 0x1C:  bne x5, x0, Loop  op=0x63, rd=0, fct3=0x1, rs1=5, rs2=0, imm=?

    ## Calculate branch offset: Target (0x08) - Branch PC (0x1C) = -20 bytes
    branch_offset = -20

    instructions = [
        encode_instruction(op=0x03, rd=7, fct3=0x2, rs1=10, rs2=0, imm=0),   ## lw x7, 0(x10)
        encode_instruction(op=0x13, rd=5, fct3=0x0, rs1=0, rs2=0, imm=3),    ## addi x5, x0, 3
        ## Loop Start (PC = 0x08)
        encode_instruction(op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=0),    ## lw x6, 0(x7)
        encode_instruction(op=0x13, rd=6, fct3=0x0, rs1=6, rs2=0, imm=1),    ## addi x6, x6, 1
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=6, imm=0),    ## sw x6, 0(x7)
        encode_instruction(op=0x13, rd=7, fct3=0x0, rs1=7, rs2=0, imm=4),    ## addi x7, x7, 4
        encode_instruction(op=0x13, rd=5, fct3=0x0, rs1=5, rs2=0, imm=-1),   ## addi x5, x5, -1
        ## Branch back to Loop (PC = 0x1C)
        encode_instruction(op=0x63, rd=0, fct3=0x1, rs1=5, rs2=0, imm=branch_offset), # bne x5, x0, Loop
    ]

    bin_file = 'branch_instructions.bin'
    csv_file = 'branch_simulation.csv'

    print(f"--- Running Branch Simulation ---")
    print(f"Writing instructions to {bin_file}")
    with open(bin_file, 'wb') as f:
        for i, instr in enumerate(instructions):
            print(f"  PC 0x{i*4:02x}: 0x{instr:08x}")
            f.write(struct.pack('<I', instr))

    print(f"Running simulator and writing to {csv_file}")
    simulator = PipelineSimulator(bin_file)
    simulator.run(csv_file)
    print(f"--- Branch Simulation Complete ---")

if(__name__ == "__main__"):
    main() 