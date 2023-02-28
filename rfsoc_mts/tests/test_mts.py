from rfsoc_mts import mtsOverlay
import numpy as np
from scipy import signal

def test_mts():
    ol = mtsOverlay('mts.bit')
    ol.verify_clock_tree()
    ACTIVE_DAC_TILES = 0b0011
    ACTIVE_ADC_TILES = 0b0011
    DAC_SR = 4.0E9  # Sample rate of DACs and ADCs is 4.0 GHz
    Fc = 250.0E6 # Set center frequency of waveform to 250.0 MHz
    DAC_Amplitude = 16383.0 # 14bit DAC +16383/-16384
    X_axis = (1/DAC_SR) * np.arange(0,ol.dac_player.shape[0])
    DAC_sinewave = DAC_Amplitude * np.sin(2*np.pi*Fc*X_axis)
    ol.dac_player[:] = np.int16(DAC_sinewave)
    AlignedCaptureSamples = np.zeros((3,len(ol.adc_capture_chA)),dtype=np.int16)
    ol.init_tile_sync()
    ol.verify_clock_tree()
    ol.sync_tiles(dacTiles=ACTIVE_DAC_TILES, adcTiles=ACTIVE_ADC_TILES)
    iterations = 128
    for i in range(iterations):
        ol.internal_capture(AlignedCaptureSamples)
        N = len(AlignedCaptureSamples[0])  # choose power of two for efficiency
        Tile0 = AlignedCaptureSamples[0][:N]/2**15
        TileN = AlignedCaptureSamples[2][:N]/2**15
        x_corr = signal.fftconvolve(TileN, Tile0[::-1], mode='full')
        lag0 = np.argmax(x_corr)
        assert (lag0 == (N-1))
    return(True)
