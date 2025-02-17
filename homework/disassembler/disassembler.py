import numpy as np

def sign_extend(value, bits):
    """Sign extend the given value from the specified number of bits."""
    value = int(value)  ## Prevents overflow.
    sign_bit = 1 << (bits - 1)
    if(value & sign_bit):
        value -= (1 << bits)
    return value

def decode_R_type(inst):
    ## R-type: [funct7 | rs2 | rs1 | funct3 | rd | opcode]
    rd     = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1    = (inst >> 15) & 0x1F
    rs2    = (inst >> 20) & 0x1F
    funct7 = (inst >> 25) & 0x7F

    if(funct3 == 0x0):
        if(funct7 == 0x00):
            mnemonic = "add"
        elif(funct7 == 0x20):
            mnemonic = "sub"
        else:
            mnemonic = "unknown"
    else:
        mnemonic = "unknown"

    return f"{mnemonic} x{rd}, x{rs1}, x{rs2}"

def decode_I_type(inst, opcode):
    ## I-type: [imm (12 bits) | rs1 | funct3 | rd | opcode]
    rd     = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1    = (inst >> 15) & 0x1F
    imm    = (inst >> 20) & 0xFFF
    imm    = sign_extend(imm, 12)
    
    if(opcode == 0x13):
        ## I-type arithmetic immediate instructions.
        i_type_arith = {
            0x0: "addi",
            0x2: "slti",
            0x3: "sltiu",
            0x4: "xori",
            0x6: "ori",
            0x7: "andi"
        }
        mnemonic = i_type_arith.get(funct3, None)
        if(mnemonic):
            return f"{mnemonic} x{rd}, x{rs1}, {imm}"
        else:
            return f"unknown_I x{rd}, x{rs1}, {imm}"
    elif(opcode == 0x03):
        ## Load instructions: choose mnemonic based on funct3.
        if(funct3 == 0x0):
            mnemonic = "lb"
        elif(funct3 == 0x1):
            mnemonic = "lh"
        elif(funct3 == 0x2):
            mnemonic = "lw"
        elif(funct3 == 0x4):
            mnemonic = "lbu"
        elif(funct3 == 0x5):
            mnemonic = "lhu"
        else:
            mnemonic = "unknown_load"

        return f"{mnemonic} x{rd}, {imm}(x{rs1})"
    
    else:
        return "unknown_I_type"

def decode_S_type(inst):
    ## S-type: immediate is split between bits [11:5] and [4:0].
    imm4_0  = (inst >> 7) & 0x1F
    imm11_5 = (inst >> 25) & 0x7F
    imm     = (imm11_5 << 5) | imm4_0
    imm     = sign_extend(imm, 12)
    funct3  = (inst >> 12) & 0x7
    rs1     = (inst >> 15) & 0x1F
    rs2     = (inst >> 20) & 0x1F

    ## Only decode store word (sw); you can add sb/sh if needed.
    if(funct3 == 0x2):
        mnemonic = "sw"
    elif(funct3 == 0x0):
        mnemonic = "sb"
    elif(funct3 == 0x1):
        mnemonic = "sh"
    else:
        mnemonic = "unknown_store"
    return f"{mnemonic} x{rs2}, {imm}(x{rs1})"

def decode_SB_type(inst):
    ## SB-type: Branch instructions.
    ## immediate is built from multiple parts:
    ## imm[12] from bit 31, imm[11] from bit 7,
    ## imm[10:5] from bits 30-25, imm[4:1] from bits 11-8.
    bit12  = (inst >> 31) & 0x1
    bit11  = (inst >> 7) & 0x1
    imm10_5 = (inst >> 25) & 0x3F
    imm4_1 = (inst >> 8) & 0xF
    imm = (bit12 << 12) | (bit11 << 11) | (imm10_5 << 5) | (imm4_1 << 1)
    imm = sign_extend(imm, 13)
    funct3 = (inst >> 12) & 0x7
    rs1    = (inst >> 15) & 0x1F
    rs2    = (inst >> 20) & 0x1F

    if(funct3 == 0x0):
        mnemonic = "beq"
    elif(funct3 == 0x1):
        mnemonic = "bne"
    elif(funct3 == 0x4):
        mnemonic = "blt"
    elif(funct3 == 0x5):
        mnemonic = "bge"
    elif(funct3 == 0x6):
        mnemonic = "bltu"
    elif(funct3 == 0x7):
        mnemonic = "bgeu"
    else:
        mnemonic = "unknown_branch"

    return f"{mnemonic} x{rs1}, x{rs2}, {imm}"

def decode_U_type(inst, opcode):
    ## U-type: immediate in bits [31:12] shifted left by 12.
    rd  = (inst >> 7) & 0x1F
    imm = inst & 0xFFFFF000
    if(opcode == 0x37):
        mnemonic = "lui"
    elif(opcode == 0x17):
        mnemonic = "auipc"
    else:
        mnemonic = "unknown_U"
    return f"{mnemonic} x{rd}, {imm}"

def decode_instruction(inst):
    ## The opcode is in the lowest 7 bits.
    opcode = inst & 0x7F
    if(opcode == 0x33):
        return decode_R_type(inst)
    elif(opcode == 0x13 or opcode == 0x03):
        return decode_I_type(inst, opcode)
    elif(opcode == 0x23):
        return decode_S_type(inst)
    elif(opcode == 0x63):
        return decode_SB_type(inst)
    elif(opcode == 0x37 or opcode == 0x17):
        return decode_U_type(inst, opcode)
    else:
        return "unknown_instruction"

def main():
    filename = "risc-v_instructions.bin"
    try:
        instructions = np.fromfile(filename, dtype=np.uint32)
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        return

    disassembled_instructions = []
    for inst in instructions:
        disassembled_line = decode_instruction(inst)
        disassembled_instructions.append(disassembled_line)

    for line in disassembled_instructions:
        print(line)

    with open("disassembled.txt", "w") as f:
        for line in disassembled_instructions:
            f.write(line + "\n")

if(__name__ == "__main__"):
    main() 


## Resulting instructions:
## lw x7, 0(x10)
## addi x5, x0, 3
## lw x6, 0(x7)
## xori x6, x6, 32
## sw x6, 0(x7)
## addi x7, x7, 4
## addi x5, x5, -1
## bne x5, x0, -40

## I checked with Professor Siddappa via email and he said that the instructions are correct.