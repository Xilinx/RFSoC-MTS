# -------------------------------------------------------------------------------------------------
# Copyright (C) 2023 Advanced Micro Devices, Inc
# SPDX-License-Identifier: MIT
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --
import pynq
from pynq import Overlay, MMIO
import xrfclk
import xrfdc
import numpy as np
import time
import os

MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
LMK_FREQ = 500.0
LMX_FREQ = 4000.0
CLOCKWIZARD_LOCK_ADDRESS = 0x0004
CLOCKWIZARD_RESET_ADDRESS = 0x0000
CLOCKWIZARD_RESET_TOKEN = 0x000A
MTS_START_TILE = 0x01
MAX_DAC_TILES = 4
MAX_ADC_TILES = 4

class mtsOverlay(Overlay):
    """
    The MTS overlay demonstrates the RFSoC multi-tile synchronization capability that enables
    multiple RF DAC and ADC tiles to achieve latency alignment. This capability is key to enabling
    Massive MIMO, phased array RADAR applications and beamforming.
    """
    def __init__(self, bitfile_name='mts.bit', **kwargs):
        """
         This overlay class supports the MTS overlay.  It configures the PL gpio, internal memories,
         PL-DRAM and DMA interfaces.  Additional helper methods are provided to: configure and verify
         MTS, verify the DACRAM and read captured samples from the internal ADC
         memories and the PL-DDR4 memory.  In addition to the bitfile_name, the active ADC and DAC
         tiles must be provided to use in the MTS initialization.
        """
        dts = pynq.DeviceTreeSegment(resolve_binary_path('ddr4.dtbo'))
        if not dts.is_dtbo_applied():
            dts.insert()
        # must configure CLK104 before loading overlay since the overlay needs
        # the LMK04828 PL_CLK and PL_SYSREF clocks
        xrfclk.set_ref_clks(lmk_freq = LMK_FREQ, lmx_freq = LMX_FREQ)
        time.sleep(0.5)        
        super().__init__(resolve_binary_path(bitfile_name), **kwargs)
        self.xrfdc = self.usp_rf_data_converter_1       
        
        # map PL GPIO registers
        self.dac_enable =  self.gpio_control.axi_gpio_dac.channel1[0]       
        self.trig_cap = self.gpio_control.axi_gpio_bram_adc.channel1[0]
        self.fifo_flush = self.gpio_control.axi_gpio_fifoflush.channel1[0]
        
        # DAC Player Memory - DACs will play this waveform
        self.dac_player = self.memdict_to_view("hier_dac_play/axi_bram_ctrl_0")
   
        # DAC Capture Memory - to verify DAC AWG for diagnostics
        self.dac_capture = self.memdict_to_view("hier_dac_cap/axi_bram_ctrl_0")
        
        # ADC Capture Memories
        self.adc_capture_chA = self.memdict_to_view("hier_adc0_cap/axi_bram_ctrl_0")
        self.adc_capture_chB = self.memdict_to_view("hier_adc1_cap/axi_bram_ctrl_0")        
        self.adc_capture_chC = self.memdict_to_view("hier_adc2_cap/axi_bram_ctrl_0")
        
        # Reset GPIOs and bring to known state
        self.dac_enable.off()
        self.trig_cap.off() 
        self.fifo_flush.off() # active low flush of the DMA fifo

        self.adc_dma = self.deepCapture.axi_dma_adc # PL DMA to DDR4 memory
        self.ADCdeepcapture = self.memdict_to_view("ddr4_0")

    def memdict_to_view(self, ip, dtype='int16'):
        """ Configures access to internal memory via MMIO"""
        baseAddress = self.mem_dict[ip]["phys_addr"]
        mem_range = self.mem_dict[ip]["addr_range"]
        ipmmio = MMIO(baseAddress, mem_range)
        return ipmmio.array[0:ipmmio.length].view(dtype)

    def sync_tiles(self, dacTiles=0, adcTiles=0):
        """ Configures RFSoC MTS alignment"""
        # Set which RF tiles use MTS and turn MTS off
        # check settings of the adc and dac tiles before continuing
        if (adcTiles > ((1 << MAX_ADC_TILES)-1)):
            raise Exception("Illegal number of ADC tiles given")
        if (dacTiles > ((1 << MAX_DAC_TILES)-1)):
            raise Exception("Illegal number of ADC tiles given")        
        if ((adcTiles == 0) & (dacTiles == 0)):
            raise Exception("No active ADC or DAC tiles specified!")
        if ((adcTiles & 0x01) == 0):
            raise Exception("MTS chain required to start at ADC Tile 0 / Bank 224")
        if ((dacTiles & 0x01) == 0):
            raise Exception("MTS chain required to start at DAC Tile 0 / Bank 228")
        self.xrfdc.mts_dac_config.RefTile = 0  # MTS starts at DAC Tile 228
        self.xrfdc.mts_adc_config.RefTile = 0  # MTS starts at ADC Tile 224
        self.xrfdc.mts_dac_config.Target_Latency = -1
        self.xrfdc.mts_adc_config.Target_Latency = -1
        if dacTiles > 0:
            self.xrfdc.mts_dac_config.Tiles = dacTiles # group defined in binary 0b1111
            self.xrfdc.mts_dac_config.SysRef_Enable = 1
            self.xrfdc.mts_dac()
        else:
            self.xrfdc.mts_dac_config.Tiles = 0x0
            self.xrfdc.mts_dac_config.SysRef_Enable = 0
        if adcTiles > 0:
            self.xrfdc.mts_adc_config.Tiles = adcTiles 
            self.xrfdc.mts_adc_config.SysRef_Enable = 1
            self.xrfdc.mts_adc()
        else:
            self.xrfdc.mts_adc_config.Tiles = 0x0
            self.xrfdc.mts_adc_config.SysRef_Enable = 0

    def init_tile_sync(self, adcTiles=0, dacTiles=0):
        """ Resets the MTS alignment engine"""
        self.sync_tiles(MTS_START_TILE, MTS_START_TILE)
        # Reset MTS ClockWizard MMCM - refer to PG065
        self.clocktreeMTS.MTSclkwiz.mmio.write_reg(CLOCKWIZARD_RESET_ADDRESS, CLOCKWIZARD_RESET_TOKEN)
        time.sleep(0.1)
        # Reset only user selected DAC tiles
        bitvector = dacTiles
        for n in range(MAX_DAC_TILES):
            if (bitvector & 0x1):
                self.xrfdc.dac_tiles[n].Reset()
            bitvector = bitvector >> 1
        # Reset ADC FIFO of only user selected tiles - restarts MTS engine
        for toggleValue in range(0,1):
            bitvector = adcTiles
            for n in range(MAX_ADC_TILES):
                if (bitvector & 0x1):
                    self.xrfdc.adc_tiles[n].SetupFIFOBoth(toggleValue)
                bitvector = bitvector >> 1
 
    def verify_clock_tree(self):
        """ Verify the PL and PL_SYSREF clocks are active by verifying an MMCM is in the LOCKED state"""
        Xstatus = self.clocktreeMTS.MTSclkwiz.read(CLOCKWIZARD_LOCK_ADDRESS) # reads the LOCK register
        # the ClockWizard AXILite registers are NOT fully mapped: refer to PG065
        if (Xstatus != 1):
            raise Exception("The MTS ClockTree has failed to LOCK. Please verify board clocking configuration")

    def trigger_capture(self):
        """ Internal loopback of DAC waveform to internal capture mirror"""        
        self.trig_cap.off()
        self.dac_enable.off()
        self.dac_enable.on()
        self.trig_cap.on() # actually triggers adc[A..C] to capture too
        time.sleep(0.5)
        self.trig_cap.off()

    def internal_capture(self, triplebuffer):
        """ Captures ADC samples from three channels and stores to internal memories """
        if not np.issubdtype(triplebuffer.dtype, np.int16):
            raise Exception("buffer not defined or np.int16!")
        if not triplebuffer.shape[0] == 3:
            raise Exception("buffer must be of shape(3, N)!")
        self.trigger_capture()
        triplebuffer[0] = np.copy(self.adc_capture_chA[0:len(triplebuffer[0])])
        triplebuffer[1] = np.copy(self.adc_capture_chB[0:len(triplebuffer[1])])
        triplebuffer[2] = np.copy(self.adc_capture_chC[0:len(triplebuffer[2])])

    def dram_capture(self, buffer):
        """ Captures ADC samples to the PL-DRAM memory notebook provided buffer """
        if type(buffer) != pynq.buffer.PynqBuffer:
            raise Exception("A PYNQ allocated buffer is required!")

        if not np.issubdtype(buffer.dtype, np.int16):
            raise Exception("buffer not defined or np.int16")
        
        self.dac_enable.on()
        self.adc_dma.register_map.S2MM_DMACR.Reset = 1
        self.adc_dma.recvchannel.stop()
        self.fifo_flush.off() # clear FIFO
        # because TLAST is not used, we must soft-reset the S2MM/recvchannel
        self.adc_dma.register_map.S2MM_DMACR.Reset = 0
        self.adc_dma.recvchannel.start()
        self.adc_dma.recvchannel.transfer(buffer)
        self.fifo_flush.on() # enable FIFO and samples will start flowing

def resolve_binary_path(bitfile_name):
    """ this helper function is necessary to locate the bit file during overlay loading"""
    if os.path.isfile(bitfile_name):
        return bitfile_name
    elif os.path.isfile(os.path.join(MODULE_PATH, bitfile_name)):
        return os.path.join(MODULE_PATH, bitfile_name)
    else:
        raise FileNotFoundError(f'Cannot find {bitfile_name}.')
# -------------------------------------------------------------------------------------------------

