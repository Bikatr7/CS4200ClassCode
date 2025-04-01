import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    instructions = [
        encode_instruction(0x03, 7, 0x2, 10, 0),   ## lw x7, 0(x10)
        encode_instruction(0x03, 6, 0x2, 7, 0),    ## lw x6, 0(x7)
        encode_instruction(0x13, 6, 0x0, 6, 1),    ## addi x6, x6, 1
        encode_instruction(0x23, 0, 0x2, 7, 6),    ## sw x6, 0(x7)
        encode_instruction(0x03, 6, 0x2, 7, 4),    ## lw x6, 4(x7)
        encode_instruction(0x13, 6, 0x0, 6, 1),    ## addi x6, x6, 1
        encode_instruction(0x23, 0, 0x2, 7, 6),    ## sw x6, 4(x7)
        encode_instruction(0x03, 6, 0x2, 7, 8),    ## lw x6, 8(x7)
        encode_instruction(0x13, 6, 0x0, 6, 1),    ## addi x6, x6, 1
        encode_instruction(0x23, 0, 0x2, 7, 6),    ## sw x6, 8(x7)
    ]
    
    with open('unrolled_instructions.bin', 'wb') as f:
        for instr in instructions:
            f.write(struct.pack('<I', instr))

    simulator = PipelineSimulator('unrolled_instructions.bin')
    simulator.run('unrolled_simulation.csv')

if(__name__ == "__main__"):
    main() 