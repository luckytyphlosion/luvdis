import yaml
import pathlib
import difflib
import betterdiff
import json
import re
import struct

from luvdis import __version__
from luvdis.config import read_config
from luvdis.common import eprint, set_debug, dprint
from luvdis.rom import ROM
from luvdis.analyze import State, BASE_ADDRESS, END_ADDRESS, THUMB, BYTE, WORD

subroutine_prototype_regex = re.compile(r"^AIScript_(\w+)\([^\)]+\)[^;]*$")

def disasm(rom, output, functions, debug, start, stop, macros, guess, min_calls, min_length, default_mode, no_parse_functions, subroutine_name_lookup, constpool_start_to_end_map, whole_rom_as_words):
    """ Analyze and disassemble a GBA ROM. """
    set_debug(debug)
    rom = ROM(rom, detect=False)
    state = State(functions, min_calls, min_length, start, stop, macros, omit_extraneous=True, no_parse_functions=no_parse_functions, subroutine_name_lookup=subroutine_name_lookup, constpool_start_to_end_map=constpool_start_to_end_map, whole_rom_as_words=whole_rom_as_words)
    state.analyze_rom(rom, guess)
    state.dump(rom, output, None, default_mode)

def generate_expected_output_and_subroutine_name_lookup(ai_scripts_directory, test_basename):
    asm_lines = []
    subroutine_name_lookup = {}
    skipped_first_func = False

    with open(ai_scripts_directory / f"{test_basename}.ai", "r") as f:
        lines = f.read().splitlines()

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("///"):
            asm_line = line.split("///", maxsplit=1)[1]
            if asm_line.startswith(".pool") or not asm_line.startswith(".") and not asm_line.endswith(":"):
                asm_line = f"\t{asm_line}"

            asm_lines.append(asm_line)
        # function subroutine replacement
        elif (match_obj := subroutine_prototype_regex.match(stripped_line)):
            if skipped_first_func:
                subroutine_name_lookup[len(subroutine_name_lookup)] = match_obj.group(1)
            else:
                skipped_first_func = True

    return asm_lines, subroutine_name_lookup

def read_thumb_cmd_functions(ai_config):
    aicmd_syms_filename = ai_config["aicmd_syms"]
    with open(aicmd_syms_filename, "r") as f:
        aicmd_syms_str_keys = json.load(f)

    aicmd_syms = {int(addr_str, 16): name for addr_str, name in aicmd_syms_str_keys.items()}

    return aicmd_syms

def read_constpool_start_to_end_map(ai_config):
    constpool_start_to_end_map_filename = ai_config["constpool_start_to_end_map_filename"]

    with open(constpool_start_to_end_map_filename, "r") as f:
        constpool_start_to_end_map_str_keys_values = json.load(f)

    constpool_start_to_end_map = {int(start_addr_str, 16): int(end_addr_str, 16) for start_addr_str, end_addr_str in constpool_start_to_end_map_str_keys_values.items()}

    return constpool_start_to_end_map

def main():
    with open("ai_config.yml", "r") as f:
        ai_config = yaml.safe_load(f)

    with open(ai_config["test_basenames"], "r") as f:
        test_basenames = [line.split(", ") for line in f.read().strip().splitlines()]

    dump_directory = pathlib.Path(ai_config["dump_directory"])
    ai_scripts_directory = pathlib.Path(ai_config["ai_scripts_directory"])

    differ = difflib.Differ()

    no_parse_functions = read_thumb_cmd_functions(ai_config)
    constpool_start_to_end_map = read_constpool_start_to_end_map(ai_config)
    with open(ai_config["whole_rom_filename"], "rb") as f:
        whole_rom = f.read()

    whole_rom_as_words = struct.unpack(f"<{len(whole_rom) // 4}I", whole_rom)

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

        expected_output, subroutine_name_lookup = generate_expected_output_and_subroutine_name_lookup(ai_scripts_directory, test_basename)

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
            default_mode=BYTE,
            no_parse_functions=no_parse_functions,
            subroutine_name_lookup=subroutine_name_lookup,
            constpool_start_to_end_map=constpool_start_to_end_map,
            whole_rom_as_words=whole_rom_as_words
        )



        with open(output_filename, "r") as f:
            actual_output = [line for line in f.read().splitlines() if line != ""]

        delta = betterdiff.better_diff(expected_output, actual_output, as_string=True)
        with open(f"output/{test_basename}_result.dump", "w+") as f:
            f.write(delta)

if __name__ == "__main__":
    main()
