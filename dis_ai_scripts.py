import yaml
import pathlib

from luvdis import __version__
from luvdis.config import read_config
from luvdis.common import eprint, set_debug, dprint
from luvdis.rom import ROM
from luvdis.analyze import State, BASE_ADDRESS, END_ADDRESS, THUMB, BYTE, WORD

def disasm(rom, output, functions, debug, start, stop, macros, guess, min_calls, min_length, default_mode,
           **kw):
    """ Analyze and disassemble a GBA ROM. """
    for k, v in kw.items():
        print(k, v)
    set_debug(debug)
    rom = ROM(rom, detect=False)
    state = State(functions, min_calls, min_length, start, stop, macros, omit_extraneous=True)
    state.analyze_rom(rom, guess)
    state.dump(rom, output, None, default_mode)

def main():
    with open("ai_config.yml", "r") as f:
        ai_config = yaml.safe_load(f)

    with open(ai_config["test_basenames"], "r") as f:
        test_basenames = [line.split(", ") for line in f.read().strip().splitlines()]

    dump_directory = pathlib.Path(ai_config["dump_directory"])

    for test_basename, test_start_function_name in test_basenames:
        test_dump_filename = str(dump_directory / f"{test_basename}.bin")
        test_info_filepath = dump_directory / f"{test_basename}.txt"
        addr_map = {}

        with open(test_info_filepath, "r") as f:
            starts_at_zero, = f.read().strip().splitlines()
            #print(f"starts_at_zero: \"{starts_at_zero}\"")

            if starts_at_zero == "true":
                start_addr = 0x0
            else:
                start_addr = 0x2

            addr_map[start_addr] = test_start_function_name, None

        output_filename = f"output/{test_basename}_actual.s"
        disasm(
            rom=test_dump_filename,
            output=output_filename,
            functions=addr_map,
            debug=True,
            start=0x0,
            stop=0x10000,
            macros=None,
            guess=True,
            min_calls=1,
            min_length=1,
            default_mode=BYTE
        )

if __name__ == "__main__":
    main()
