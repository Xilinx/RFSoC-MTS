// -------------------------------------------------------------------------------------------------
// Copyright (C) 2023 Advanced Micro Devices, Inc
// SPDX-License-Identifier: MIT
// ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --
`timescale 1ns / 1ps

module ADCRAMcapture #(parameter DWIDTH = 256, parameter MEM_SIZE_BYTES = 65536) (
  (* X_INTERFACE_PARAMETER = "MASTER_TYPE BRAM_CTRL, READ_WRITE_MODE READ, MEM_SIZE 32768, MEM_WIDTH 256" *)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A DIN" *)
  output reg [DWIDTH-1:0] bram_wdata, // Data In Bus (optional)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A WE" *)
  output reg [DWIDTH/8-1:0] bram_we, // Byte Enables (optional)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A EN" *)
  output reg bram_en, // Chip Enable Signal (optional)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A DOUT" *)
  input wire [DWIDTH-1:0] bram_rdata, // Data Out Bus (optional)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A ADDR" *)
  output reg [31:0] bram_addr, // Address Signal (required)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A CLK" *)
  output wire bram_clk, // Clock Signal (required)

  (* X_INTERFACE_INFO = "xilinx.com:interface:bram:1.0 BRAM_A RST" *)
  output wire bram_rst, // Reset Signal (required)

  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 axis_clk CLK" *)
  (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF CAP_AXIS, ASSOCIATED_RESET axis_aresetn" *)
  input wire axis_clk,

  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 axis_aresetn RST" *)
  input  wire              axis_aresetn,
  input  wire [DWIDTH-1:0] CAP_AXIS_tdata,
  output wire              CAP_AXIS_tready,
  input  wire              CAP_AXIS_tvalid,

  input  wire              trig_cap );

  localparam ADDR_INC = DWIDTH/8;
  localparam CAP_SIZE = MEM_SIZE_BYTES;
  localparam TRIGCAP_HI = 15;
  (* ASYNC_REG="TRUE" *) reg [TRIGCAP_HI:0] trig_cap_p = 0;

  assign bram_clk = axis_clk;
  assign bram_rst = ~axis_aresetn;
  assign CAP_AXIS_tready = 1'b1;
  assign trig_cap_posedge = ~trig_cap_p[TRIGCAP_HI] & trig_cap_p[TRIGCAP_HI-1];
 
  //sync trig_cap to cap_clk and add bit for rising pulse detect
  always @(posedge axis_clk) begin
    if (~axis_aresetn) begin
      trig_cap_p <= 0;
    end else begin
      trig_cap_p <= {trig_cap_p[TRIGCAP_HI-1:0], trig_cap};
    end
  end

  //BRAM Port B address control
  always @(posedge axis_clk) begin
    bram_wdata <= CAP_AXIS_tdata;  // pipline registers for in data to bram and passthrough outputs
    if (~axis_aresetn) begin
      bram_addr <= 0;
      bram_we   <= 0;
      bram_en   <= 0;
    end else begin
      if (trig_cap_posedge) begin
        bram_addr <= 0;
        bram_we   <= CAP_AXIS_tvalid ? {DWIDTH/8{1'b1}} : {DWIDTH/8{1'b0}};
        bram_en   <= 1'b1;
      end else begin
        if (bram_en && CAP_AXIS_tvalid) begin
          if (bram_addr < (CAP_SIZE-ADDR_INC)) begin
            bram_addr <= bram_addr + ADDR_INC;
            bram_we   <= {DWIDTH/8{1'b1}};
            bram_en   <= 1'b1;
          end else begin
            bram_we <= {DWIDTH/8{1'b0}};
            bram_en <= 1'b0;
          end
        end
      end
    end
  end
endmodule
