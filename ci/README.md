# Source Project

[500lines/ci](https://github.com/aosabook/500lines/ci)


# Refactor Log

## repo\_observer.py

1. Use click instead of argparse (As argument don't support help message now, remove the help message temporarily) 

2. remove redudent code in *update\_repor.sh*, extract method get\_commmit\_id for repeated codes

3. update status command message, use the same format `<command>:<message>` as others

## dispatcher.py

1. Use click instead of argparse

2. move out the inner method *runner\_checker* and *redistribute*, to make the code clear 

3. remove if..else... for commands, use dictionary with methods instead.

## test\_runner.py
