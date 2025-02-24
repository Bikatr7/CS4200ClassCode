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


async def perform_negate(dut) -> None:
    """
    Perform the two's complement.

    :param dut: DUT object from cocotb
    :return: None
    """
    raise NotImplementedError("Implement negate")

def perform_sub(dut) -> None:
    """
    sub rd, rs1, rs2

    :param dut: Dut object from cocotb
    :param s1: First value as described in R sub
    :param s2: Second value as described in R sub
    :return: None
    """
    raise NotImplementedError("Implement sub")


async def set_gt(dut):
    """
    In the same format as slt, rd, rsq, rs2 perform the operation to set the output LSB bit to rs1 > rs2.

    :param dut:
    :return:
    """


async def set_gte(dut):
    """
    In the same format as slt rd, rs1, rs2 perform the operation to set the output LSB bit to rs1 >= rs2.

    :param dut: DUT object from cocotb
    :return:
    """


async def f_set_e(dut):
    """
    In the same format as feq.s rd, rs1, rs2 perform a floating point equal comparison.

    :param dut:
    :return:
    """


async def f_set_lt(dut):
    """
    In the same format as flt.s rd, rs1, rs2 perform a floating point less than comparison.

    :param dut:
    :return:
    """


async def f_set_lte(dut):
    """
    In the same format as fle.s rd, rs1, rs2 perform a floating point less than or equal comparison.

    :param dut:
    :return:
    """


async def perform_multiplication(dut):
    """
    In the same format as mul rd, rs1, rs2 perform multiplication.

    :param dut:
    :return:
    """


async def perform_division(dut):
    """
    In the same format as mul rd, rs1, rs2 perform multiplication.

    :param dut:
    :return:
    """

@cocotb.test()
async def run_alu_sim(dut):
    clock = Clock(dut.clk, period=10, units='ns') # This assigns the clock into the ALU
    cocotb.start_soon(clock.start(start_high=False))


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

if __name__ == '__main__':
    test_via_cocotb()
