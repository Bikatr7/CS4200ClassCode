import struct
from hazards_simulator import PipelineSimulator, encode_instruction

def main():
    instructions = [
        encode_instruction(0x03, 7, 0x2, 10, 0),   ## lw x7, 0(x10)
        encode_instruction(0x13, 5, 0x0, 0, 3),    ## addi x5, x0, 3
        ## Loop:
        encode_instruction(0x03, 6, 0x2, 7, 0),    ## lw x6, 0(x7)
        encode_instruction(0x13, 6, 0x0, 6, 1),    ## addi x6, x6, 1
        encode_instruction(0x23, 0, 0x2, 7, 6),    ## sw x6, 0(x7)
        encode_instruction(0x13, 7, 0x0, 7, 4),    ## addi x7, x7, 4
        encode_instruction(0x13, 5, 0x0, 5, -1),   ## addi x5, x5, -1
        ## Branch back to Loop (offset -20 bytes, divide by 2 for encoding)
        encode_instruction(0x63, 0, 0x1, 5, 0),    ## bne x5, x0, Loop (-20/2 = -10)
    ]
    
    with open('branch_instructions.bin', 'wb') as f:
        for instr in instructions:
            f.write(struct.pack('<I', instr))
    
    simulator = PipelineSimulator('branch_instructions.bin')
    simulator.run('branch_simulation.csv')

if(__name__ == "__main__"):
    main() 