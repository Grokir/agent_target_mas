import asyncio

from tests.colorize_print   import *
from tests.test_db_agent    import test_base_work as db_base_work
from tests.test_code_agent  import test_base_work as code_base_work
from tests.test_coord_agent import test_base_work as coord_base_work


def run_tests():
    tests_list = [
        # db_base_work,
        # code_base_work,
        coord_base_work,
    ]

    for test in tests_list:
        tres = asyncio.run(test())
        print(f"[{bold(green('+')) if tres[1] else bold(red('-'))}] {tres[0]}: {bold(green('PASS')) if tres[1] else bold(red('FAIL'))}{cyan(f" ::{tres[2]}" if tres[2] else '')}")