import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    reordered_instructions = [
        ## PC 0x00: lw x7, 0(x10)
        encode_instruction(op=0x03, rd=7, fct3=0x2, rs1=10, rs2=0, imm=0),
        ## PC 0x04: lw x8, 4(x7)
        encode_instruction(op=0x03, rd=8, fct3=0x2, rs1=7, rs2=0, imm=4),
        ## PC 0x08: lw x9, 8(x7)
        encode_instruction(op=0x03, rd=9, fct3=0x2, rs1=7, rs2=0, imm=8),
        ## PC 0x0C: addi x10, x6, 1  (Independent, moved up)
        encode_instruction(op=0x13, rd=10, fct3=0x0, rs1=6, rs2=0, imm=1),
        ## PC 0x10: addi x11, x8, 1  (Depends on lw x8 @ 0x04)
        encode_instruction(op=0x13, rd=11, fct3=0x0, rs1=8, rs2=0, imm=1),
        ## PC 0x14: addi x12, x9, 1  (Depends on lw x9 @ 0x08)
        encode_instruction(op=0x13, rd=12, fct3=0x0, rs1=9, rs2=0, imm=1),
        ## PC 0x18: sw x10, 0(x7)   (Depends on lw x7 @ 0x00, addi x10 @ 0x0C)
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=10, imm=0),
        ## PC 0x1C: sw x11, 4(x7)   (Depends on lw x7 @ 0x00, addi x11 @ 0x10)
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=11, imm=4),
        ## PC 0x20: sw x12, 8(x7)   (Depends on lw x7 @ 0x00, addi x12 @ 0x14)
        encode_instruction(op=0x23, rd=0, fct3=0x2, rs1=7, rs2=12, imm=8),
    ]

    bin_file = 'dynamic_instructions.bin'
    csv_file = 'dynamic_simulation.csv'
    reorder_file = 'dynamic_reorder.txt'

    print(f"--- Running Dynamic Simulation (Reordered Sequence on 5-Stage Pipeline) ---")
    print(f"Writing reordered instructions to {reorder_file}")
    with open(reorder_file, 'w') as f:
        f.write("lw x7, 0(x10)\n")
        f.write("lw x8, 4(x7)\n")
        f.write("lw x9, 8(x7)\n")
        f.write("addi x10, x6, 1\n")
        f.write("addi x11, x8, 1\n")
        f.write("addi x12, x9, 1\n")
        f.write("sw x10, 0(x7)\n")
        f.write("sw x11, 4(x7)\n")
        f.write("sw x12, 8(x7)\n")

    print(f"Writing encoded reordered instructions to {bin_file}")
    with open(bin_file, 'wb') as f:
        for i, instr in enumerate(reordered_instructions):
             print(f"  PC 0x{i*4:02x}: 0x{instr:08x}")
             f.write(struct.pack('<I', instr))

    print(f"Running 5-stage simulator and writing to {csv_file}")
    simulator = PipelineSimulator(bin_file)
    simulator.run(csv_file)
    print(f"--- Dynamic Simulation (Reordered) Complete ---")


if(__name__ == "__main__"):
    main() 