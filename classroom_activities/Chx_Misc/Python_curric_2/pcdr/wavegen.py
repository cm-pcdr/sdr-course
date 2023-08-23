"""
A collection of misc functions
and such for this class.

Try this to start: wave_gen_prompts()
"""

import numpy as np
import matplotlib.pyplot as plt
import deal
import random
from typing import Optional, List, Tuple

from pcdr.fileio import writeRealCSV, writeComplexCSV
from pcdr.modulators import ook_modulate
from pcdr.helpers import str_to_bin_list




@deal.has()
@deal.ensure(lambda _: _.result.dtype == _.dtype)
@deal.ensure(lambda _: len(_.result) == _.num_samples)
@deal.post(lambda result: np.isfinite(result).all())
@deal.post(lambda result: (0 <= result).all())
@deal.pre(lambda _: 0 <= _.seconds < 900e6)  # arbitrarily large number
@deal.pre(lambda _: 0 <= _.num_samples < 900e6)  # arbitrarily large number
def createTimestamps(seconds: float, num_samples: int, dtype=np.float32) -> np.ndarray:
    return np.linspace(
            start=0,
            stop=seconds,
            num=num_samples,
            endpoint=False,
            dtype=dtype
        )


@deal.has()
@deal.pre(lambda _: -1e100 < _.freq < 1e100)  # arbitrarily high number that is less than the max float
@deal.pre(lambda _: (0 <= _.timestamps).all())
@deal.pre(lambda _: np.isfinite(_.timestamps).all())
@deal.pre(lambda _: _.timestamps.dtype == np.float32)
@deal.pre(lambda _: len(_.timestamps.shape) == 1)
@deal.ensure(lambda _: len(_.timestamps) == len(_.result))
def makeRealWave(timestamps: np.ndarray, freq: float):
    return np.float32(np.sin(freq * 2 * np.pi * timestamps))


@deal.has()
@deal.pre(lambda _: -1e100 < _.freq < 1e100)  # arbitrarily high number that is less than the max float
@deal.pre(lambda _: (0 <= _.timestamps).all())
@deal.pre(lambda _: np.isfinite(_.timestamps).all())
@deal.pre(lambda _: _.timestamps.dtype == np.float32)
@deal.pre(lambda _: len(_.timestamps.shape) == 1)
@deal.ensure(lambda _: len(_.timestamps) == len(_.result))
def makeComplexWave(timestamps: np.ndarray, freq: float) -> np.ndarray:
    ## Note: I don't know enough about math with complex numbers
    ## to know if freq should be restricted to real, but I figured
    ## it was better to type-annotate it as `float` rather than leaving
    ## it as `Any`.
    return np.complex64(np.exp(1j * freq * 2 * np.pi * timestamps))


@deal.has()
@deal.ensure(lambda _: len(_.result[0]) == len(_.result[1]) == _.num_samples)
@deal.pre(lambda _: 1e-10 < _.samp_rate)  # arbitrarily low number
@deal.pre(lambda _: 0 <= _.num_samples <= 10e9, message="num_samples must be between 0 and 10 billion. Upper limit is primarily to make automated testing faster")
@deal.pre(lambda _: -1e100 < _.freq < 1e100)  # arbitrarily high number that is less than the max float
def makeComplexWave_numsamps(num_samples: int, samp_rate: float, freq: float) -> Tuple[np.ndarray, np.ndarray]:
    t = num_samples / samp_rate
    timestamps = createTimestamps(seconds=t, num_samples=num_samples)
    return timestamps, makeComplexWave(timestamps, freq)


@deal.pre(lambda _: _.complex_or_real in ["r", "c"], message="Must choose 'c' or 'r' to specify if real or complex is wanted.")
def waveAndWrite(basename: str, timestamps: np.ndarray, freq, complex_or_real):
    if complex_or_real == "r":
        data = makeRealWave(timestamps, freq)
        writeRealCSV(basename + ".csv", data)
        data.tofile(basename + ".float32")
    elif complex_or_real == "c":
        data = makeComplexWave(timestamps, freq)
        writeComplexCSV(basename + ".csv", data)
        data.tofile(basename + ".complex64")


def wave_file_gen_prompts():
    print()
    print("This will create a simulated wave, and write it to two files:")
    print(" - A CSV file (for easy viewing in text editors and spreadsheet programs)")
    print(" - Either a raw float32 or complex64 file (for use in GNU Radio, URH, etc)")
    print()

    samp_rate = float(input("Pick a sample rate (samples per second): "))
    max_time = float(input("How many seconds of data would you like to generate? "))
    num_samples_original = samp_rate * max_time
    num_samples = int(num_samples_original)

    if num_samples != num_samples_original:
        raise ValueError(f"The number of samples would be {num_samples_original}, but a partial sample is meaningless.\nPlease pick a sample rate and an amount of time whose product is an integer.")

    freq = float(input("What frequency wave would you like to generate (Hz)? "))
    complex_or_real = input("Complex or Real wave? Enter c or r. ")
    filename = input("Filename? (Press enter to choose the default name, 'generated_data'.) ")
    if filename.strip() == "":
        filename = "generated_data"

    timestamps = createTimestamps(max_time, num_samples)
    print("------------------")
    print(f"Going to generate {int(num_samples)} samples.")
    print("Simulated samples were taken at these times (units are seconds):")
    print(timestamps)

    waveAndWrite(filename, timestamps, freq, complex_or_real)
    print("Done writing files.")


@deal.pre(lambda _: _.complex_or_real in ["r", "c"], message="Must choose 'c' or 'r' to specify if real or complex is wanted.")
def wave_file_gen(samp_rate: float, max_time: float, freq: float, complex_or_real: str, filename: str = 'generated_data'):
    """Units:
    samp_rate: samples per sec
    max_time: seconds
    freq: Hz
    complex_or_real: 'c' or 'r'
    """
    
    num_samples = samp_rate * max_time

    if int(num_samples) != num_samples:
        raise ValueError(f"The number of samples would be {num_samples}, but a partial sample is meaningless.\nPlease pick a sample rate and an amount of time whose product is an integer.")

    timestamps = createTimestamps(max_time, num_samples)

    waveAndWrite(filename, timestamps, freq, complex_or_real)


@deal.ensure(lambda _: len(_.result[0]) == len(_.result[1]) == len(_.baseband_sig))
@deal.post(lambda result: result.dtype == np.complex64)
def multiply_by_complex_wave(baseband_sig: np.ndarray, samp_rate: float, freq: float) -> Tuple[np.ndarray, np.ndarray]:
    timestamps, wave = makeComplexWave_numsamps(len(baseband_sig), samp_rate, freq)
    mult = baseband_sig * wave
    return timestamps, mult


@deal.post(lambda result: result.dtype == np.complex64)
def generate_ook_modulated_example_data(noise: bool = False, message_delay: bool = False, text_source: Optional[str] = None) -> np.ndarray:
    """
    Generate a file with the given `output_filename`.

    if `noise` is True, random noise will be added to the generated signal.
    if `message_delay` is True, there will be a pause before the meaningful data starts.
    if `text_source` is any string, a random sentence from it will be used as the message.
    
    Example usage:

    text_content = "These are some words, and more words. There are many words in a row in these sentences."
    generate_ook_modulated_example_data(text_source=text_content)
    """
    message = "This is an example message."
    if text_source == None:
        print(f"No text source file specified, so all generated files will contain the message '{message}'")
    else:
        sentences = text_source.split(".")
        message = random.choice(sentences) + "."
        
        
    samp_rate = random.randrange(100, 700, 100)
    bit_length = random.randrange(50, 3000, 10)
    freq = random.randrange(10, samp_rate // 5)
    
    bits = str_to_bin_list(message)
    baseband_sig = ook_modulate(bits, bit_length)
    timestamps, fully_modded = multiply_by_complex_wave(baseband_sig, samp_rate, freq)
    if message_delay:
        fully_modded = np.concatenate([
            np.zeros(random.randint(100, 1500), dtype=np.complex64),
            fully_modded
        ])
    if noise:
        fully_modded = fully_modded + np.random.normal(len(fully_modded), dtype=np.complex64)
    
    return fully_modded


def generate_ook_modulated_example_file(output_filename: str, noise: bool = False, message_delay: bool = False, text_source: Optional[str] = None):
    """
    Generate a file with the given `output_filename`.

    if `noise` is True, random noise will be added to the generated signal.
    if `message_delay` is True, there will be a pause before the meaningful data starts.
    if `text_source` is any string, a random sentence from it will be used as the message.
    
    Example usage:

    text_content = "These are some words, and more words. There are many words in a row in these sentences."
    generate_ook_modulated_example_file("generated_example_file.complex", text_source=text_content)
    """
    
    data = generate_ook_modulated_example_data(output_filename, noise, message_delay, text_source)
    data.tofile(output_filename)
