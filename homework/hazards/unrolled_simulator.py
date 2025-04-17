import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    instructions = [
        encode_instruction(op=0x03, rd=7, fct3=0x2, rs1=10, rs2=0, imm=0),   ## lw x7, 0(x10)
        encode_instruction(op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=0),    ## lw x6, 0(x7)
        encode_instruction(op=0x13, rd=6, fct3=0x0, rs1=6, rs2=0, imm=1),    ## addi x6, x6, 1
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=6, imm=0),    ## sw x6, 0(x7)
        encode_instruction(op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=4),    ## lw x6, 4(x7)
        encode_instruction(op=0x13, rd=6, fct3=0x0, rs1=6, rs2=0, imm=1),    ## addi x6, x6, 1
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=6, imm=4),    ## sw x6, 4(x7)
        encode_instruction(op=0x03, rd=6, fct3=0x2, rs1=7, rs2=0, imm=8),    ## lw x6, 8(x7)
        encode_instruction(op=0x13, rd=6, fct3=0x0, rs1=6, rs2=0, imm=1),    ## addi x6, x6, 1
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=6, imm=8),    ## sw x6, 8(x7)
    ]
    
    bin_file = 'unrolled_instructions.bin'
    csv_file = 'unrolled_simulation.csv'

    print(f"--- Running Unrolled Simulation ---")
    print(f"Writing instructions to {bin_file}")
    with open(bin_file, 'wb') as f:
        for i, instr in enumerate(instructions):
             print(f"  PC 0x{i*4:02x}: 0x{instr:08x}")
             f.write(struct.pack('<I', instr))

    print(f"Running simulator and writing to {csv_file}")
    simulator = PipelineSimulator(bin_file)
    simulator.run(csv_file)
    print(f"--- Unrolled Simulation Complete ---")

if(__name__ == "__main__"):
    main() 