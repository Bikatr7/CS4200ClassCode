## Read the README.md file IF YOU CANNOT GET IT TO WORK, NEED TO RUN FROM A CERTAIN DIRECTORY

from enum import Enum
import os

import cocotb

from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge

alu_sim_dir = os.path.abspath(os.path.join('.', 'alu_sim_dir'))

class Funct3(Enum):
    ADD = 0
    SLL = 1
    SLT = 2
    SLTU = 3
    XOR = 4
    SRL = 5
    SRA = 5
    OR = 6
    AND = 7


async def perform_not(dut) -> None:
    """
    ~

    :param dut: DUT object from cocotb
    :return: None
    """
    ## XOR with all 1's is equivalent to NOT
    dut.funct3.value = Funct3.XOR.value
    dut.s2.value = 0xFFFFFFFF  ## All 1's for XOR
    await RisingEdge(dut.clk)


async def perform_negate(dut) -> None:
    """
    Perform the two's complement.

    :param dut: DUT object from cocotb
    :return: None
    """
    ## Two's complement is NOT(value) + 1
    await perform_not(dut)
    
    ## Store the result of NOT operation
    not_value = dut.d.value
    
    ## Then add 1 to get two's complement
    dut.funct3.value = Funct3.ADD.value
    dut.s1.value = not_value
    dut.s2.value = 1
    await RisingEdge(dut.clk)


async def perform_sub(dut) -> None:
    """
    sub rd, rs1, rs2

    :param dut: Dut object from cocotb
    :param s1: First value as described in R sub
    :param s2: Second value as described in R sub
    :return: None
    """
    ## Store original s1 value
    s1_value = dut.s1.value
    
    ## 2's complement or smth
    await perform_negate(dut)
    
    ## Store negated s2
    neg_s2_value = dut.d.value
    
    ## Perform addition: s1 + (-s2)
    dut.funct3.value = Funct3.ADD.value
    dut.s1.value = s1_value
    dut.s2.value = neg_s2_value
    await RisingEdge(dut.clk)


async def set_gt(dut):
    """
    In the same format as slt, rd, rsq, rs2 perform the operation to set the output LSB bit to rs1 > rs2.

    :param dut:
    :return:
    """
    ## rs1 > rs2 is equivalent to !(rs1 <= rs2)
    ## First check if rs1 < rs2 using SLT
    dut.funct3.value = Funct3.SLT.value
    await RisingEdge(dut.clk)
    
    ## Store the result (1 if s1 < s2, 0 otherwise)
    slt_result = dut.d.value
    
    ## Check if they are equal by XORing and checking if result is 0
    dut.funct3.value = Funct3.XOR.value
    await RisingEdge(dut.clk)
    
    xor_result = dut.d.value
    
    ## Want: !(s1 < s2) && !(s1 == s2)
    ## First, negate s1 < s2 by XORing with 1
    dut.funct3.value = Funct3.XOR.value
    dut.s1.value = slt_result
    dut.s2.value = 1
    await RisingEdge(dut.clk)
    
    ## Store the negated slt_result
    not_slt = dut.d.value
    
    ## Check if xor_result is zero (meaning s1 == s2)
    dut.funct3.value = Funct3.OR.value
    dut.s1.value = xor_result
    dut.s2.value = 0
    await RisingEdge(dut.clk)
    
    ## If result is 0, they are equal, so take its NOT to get 1 when not equal
    dut.funct3.value = Funct3.XOR.value
    dut.s1.value = dut.d.value
    dut.s2.value = 1  ## XOR with 1 is NOT
    await RisingEdge(dut.clk)
    
    ## Store whether they are not equal
    not_equal = dut.d.value
    
    ## Final AND operation: (not_slt && not_equal) to get rs1 > rs2
    dut.funct3.value = Funct3.AND.value
    dut.s1.value = not_slt
    dut.s2.value = not_equal
    await RisingEdge(dut.clk)


async def set_gte(dut):
    """
    In the same format as slt rd, rs1, rs2 perform the operation to set the output LSB bit to rs1 >= rs2.

    :param dut: DUT object from cocotb
    :return:
    """
    ## rs1 >= rs2 is equivalent to !(rs1 < rs2)
    ## Use SLT to check if rs1 < rs2
    dut.funct3.value = Funct3.SLT.value
    await RisingEdge(dut.clk)
    
    ##negate the result using XOR with 1
    dut.funct3.value = Funct3.XOR.value
    dut.s1.value = dut.d.value
    dut.s2.value = 1  ##     XOR with 1 is NOT
    await RisingEdge(dut.clk)


async def f_set_e(dut):
    """
    In the same format as feq.s rd, rs1, rs2 perform a floating point equal comparison.

    :param dut:
    :return:
    """
    ## For floating point equality, we can use XOR to check if numbers are identical
    ## If XOR result is 0, they are equal
    dut.funct3.value = Funct3.XOR.value
    await RisingEdge(dut.clk)
    
    ## Check if XOR result is 0 (equal)
    ## If d == 0, then they are equal (zero signal will be set)
    ##need to check the zero signal and set d to 1 if zero is true
    
    ## Use SLTU to convert zero signal to d (comparing 0 < 1 will give 1)
    dut.funct3.value = Funct3.SLTU.value
    dut.s1.value = 0
    dut.s2.value = dut.zero.value.integer  ## This should be 1 if zero is true
    await RisingEdge(dut.clk)


async def f_set_lt(dut):
    """
    In the same format as flt.s rd, rs1, rs2 perform a floating point less than comparison.

    :param dut:
    :return:
    """
    ## For simple floating point numbers (assuming positive), can use the regular SLT
    dut.funct3.value = Funct3.SLT.value
    await RisingEdge(dut.clk)


async def f_set_lte(dut):
    """
    In the same format as fle.s rd, rs1, rs2 perform a floating point less than or equal comparison.

    :param dut:
    :return:
    """
    
    ## First check for less than
    await f_set_lt(dut)
    lt_result = dut.d.value
    
    ## Then check for equality
    original_s1 = dut.s1.value  ## Save original values
    original_s2 = dut.s2.value
    
    await f_set_e(dut)
    eq_result = dut.d.value
    
    ## Restore original values
    dut.s1.value = original_s1
    dut.s2.value = original_s2
    
    ## Perform OR to combine the results
    dut.funct3.value = Funct3.OR.value
    dut.s1.value = lt_result
    dut.s2.value = eq_result
    await RisingEdge(dut.clk)


async def perform_multiplication(dut):
    """
    In the same format as mul rd, rs1, rs2 perform multiplication.

    :param dut:
    :return:
    """
    ## Step 1: Initialize product and multiplier
    product = 0
    multiplier = dut.s2.value
    multiplicand = dut.s1.value
    
    ## Step 2: Initialize counter
    ## We're using 32-bit values, so we need 32 iterations probably
    counter = 32
    
    ## Step 3-7: Loop for each bit
    while counter > 0:
        ## Save current state
        dut.s1.value = multiplier
        dut.s2.value = 1
        
        ## Step 3: Check LSB of multiplier
        ## Use AND operation with 1 to get LSB
        dut.funct3.value = Funct3.AND.value
        await RisingEdge(dut.clk)
        
        ## If LSB is 1, add multiplicand to product
        if dut.d.value == 1:
            dut.s1.value = product
            dut.s2.value = multiplicand
            dut.funct3.value = Funct3.ADD.value
            await RisingEdge(dut.clk)
            product = dut.d.value
        
        ## Step 4-5: Shift right multiplier
        dut.s1.value = multiplier
        dut.s2.value = 1
        dut.funct3.value = Funct3.SRL.value
        dut.funct7.value = 0  ## Logical shift right
        await RisingEdge(dut.clk)
        multiplier = dut.d.value
        
        ## Step 6: Shift left multiplicand
        dut.s1.value = multiplicand
        dut.s2.value = 1
        dut.funct3.value = Funct3.SLL.value
        await RisingEdge(dut.clk)
        multiplicand = dut.d.value
        
        ## Step 7: Decrement counter
        counter -= 1
    
    ## Set the final product as the result
    dut.s1.value = product
    dut.s2.value = 0
    dut.funct3.value = Funct3.ADD.value
    await RisingEdge(dut.clk)


async def perform_division(dut):
    """
    In the same format as mul rd, rs1, rs2 perform multiplication.

    :param dut:
    :return:
    """
    ## Step 1: Initialize values
    dividend = dut.s1.value  ## This is what we're dividing
    divisor = dut.s2.value   ## This is what we're dividing by
    quotient = 0
    remainder = 0
    
    ## Step 2: Initialize counter (we're using 32-bit values)
    counter = 32
    
    ## Step A1-A8: Main division algorithm
    while counter > 0:
        ## Step A1-A2: Shift remainder left by 1 bit and set LSB to MSB of dividend
        remainder = remainder << 1
        
        ## Get MSB of dividend
        dut.s1.value = dividend
        dut.s2.value = 31  ## Position of MSB
        dut.funct3.value = Funct3.SRL.value
        dut.funct7.value = 0  ## Logical shift
        await RisingEdge(dut.clk)
        
        ## Set LSB of remainder to MSB of dividend
        msb_dividend = dut.d.value & 1
        remainder = remainder | msb_dividend
        
        ## Step A3: Shift dividend left by 1 bit
        dut.s1.value = dividend
        dut.s2.value = 1
        dut.funct3.value = Funct3.SLL.value
        await RisingEdge(dut.clk)
        dividend = dut.d.value
        
        ## Step A4-A5: Check if remainder >= divisor
        dut.s1.value = remainder
        dut.s2.value = divisor
        
        ## Use set_gte to check if remainder >= divisor
        await set_gte(dut)
        
        ## Step A6-A7: If remainder >= divisor, subtract divisor from remainder and set LSB of quotient to 1
        if dut.d.value == 1:  ## If remainder >= divisor
            ## Subtract divisor from remainder
            dut.s1.value = remainder
            dut.s2.value = divisor
            await perform_sub(dut)
            remainder = dut.d.value
            
            ## Set LSB of quotient to 1
            quotient = (quotient << 1) | 1
        else:
            ## Just shift quotient left
            quotient = quotient << 1
        
        ## Step A8: Decrement counter
        counter -= 1
    
    ## Set the final quotient as the result
    dut.s1.value = quotient
    dut.s2.value = 0
    dut.funct3.value = Funct3.ADD.value
    await RisingEdge(dut.clk)


@cocotb.test()
async def run_alu_sim(dut):
    clock = Clock(dut.clk, period=10, units='ns') ## This assigns the clock into the ALU
    cocotb.start_soon(clock.start(start_high=False))
    
    ## Wait for a few clock cycles to initialize
    for _ in range(3):
        await RisingEdge(dut.clk)
    
    ## Test basic operations
    
    ## Test ADD operation
    dut.funct3.value = Funct3.ADD.value
    dut.s1.value = 5
    dut.s2.value = 7
    await RisingEdge(dut.clk)
    
    ## Test NOT operation
    dut.s1.value = 0x0F0F0F0F
    await perform_not(dut)
    
    ## Test negate operation 
    dut.s1.value = 42
    await perform_negate(dut)
    
    ## Test subtraction
    dut.s1.value = 20
    dut.s2.value = 7
    await perform_sub(dut)
    
    ## Test multiplication
    dut.s1.value = 6
    dut.s2.value = 7
    await perform_multiplication(dut)
    
    ## Test division
    dut.s1.value = 100
    dut.s2.value = 5
    await perform_division(dut)


def test_via_cocotb():
    """
    Main entry point for cocotb
    """
    verilog_sources = [os.path.abspath(os.path.join('.', 'alu.v'))]
    runner = get_runner("verilator")
    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=[],
        hdl_toplevel="RISCALU",
        build_args=["--threads", "2"],
        build_dir=alu_sim_dir,
    )
    runner.test(hdl_toplevel="RISCALU", test_module="alu_sim")

if (__name__ == '__main__'):
    test_via_cocotb()
