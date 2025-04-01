import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    instructions = [
        encode_instruction(0x03, 7, 0x2, 10, 0),   ## lw x7, 0(x10)
        encode_instruction(0x03, 8, 0x2, 7, 4),    ## lw x8, 4(x7)
        encode_instruction(0x03, 9, 0x2, 7, 8),    ## lw x9, 8(x7)
        encode_instruction(0x13, 10, 0x0, 6, 1),   ## addi x10, x6, 1
        encode_instruction(0x13, 11, 0x0, 8, 1),   ## addi x11, x8, 1
        encode_instruction(0x13, 12, 0x0, 9, 1),   ## addi x12, x9, 1
        encode_instruction(0x23, 0, 0x2, 7, 10),   ## sw x10, 0(x7)
        encode_instruction(0x23, 0, 0x2, 7, 11),   ## sw x11, 4(x7)
        encode_instruction(0x23, 0, 0x2, 7, 12),   ## sw x12, 8(x7)
    ]
    
    with open('dynamic_reorder.txt', 'w') as f:
        f.write("lw x7, 0(x10)\n")
        f.write("lw x8, 4(x7)\n")
        f.write("lw x9, 8(x7)\n")
        f.write("addi x10, x6, 1\n")
        f.write("addi x11, x8, 1\n")
        f.write("addi x12, x9, 1\n")
        f.write("sw x10, 0(x7)\n")
        f.write("sw x11, 4(x7)\n")
        f.write("sw x12, 8(x7)\n")
    
    with open('dynamic_instructions.bin', 'wb') as f:
        for instr in instructions:
            f.write(struct.pack('<I', instr))
    
    simulator = PipelineSimulator('dynamic_instructions.bin')
    simulator.run('dynamic_simulation.csv')

if(__name__ == "__main__"):
    main() 