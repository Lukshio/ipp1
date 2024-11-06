"""
:Author: Lukáš Ježek

• 10 - chybějící parametr skriptu (je-li třeba) nebo použití zakázané kombinace parametrů;
• 11 - chyba při otevírání vstupních souborů (např. neexistence, nedostatečné oprávnění);
• 12 - chyba při otevření výstupních souborů pro zápis (např. nedostatečné oprávnění, chyba při zápisu);
• 31 - chybný XML formát ve vstupním souboru (soubor není tzv. dobře formátovaný, angl. well-formed, viz [1]);
• 32 - neočekávaná struktura XML (např. element pro argument mimo element pro instrukci, instrukce s duplicitním pořadím nebo záporným pořadím);
• 52 - chyba při sémantických kontrolách vstupního kódu v IPPcode23 (např. použití nedefinovaného návěští, redefinice proměnné);
• 53 - běhová chyba interpretace – špatné typy operandů;
• 54 - běhová chyba interpretace – přístup k neexistující proměnné (rámec existuje);
• 55 - běhová chyba interpretace – rámec neexistuje (např. čtení z prázdného zásobníku rámců);
• 56 - běhová chyba interpretace – chybějící hodnota (v proměnné, na datovém zásobníku nebo v zásobníku volání);
• 57 - běhová chyba interpretace – špatná hodnota operandu (např. dělení nulou, špatná návra tová hodnota instrukce EXIT);
• 58 - běhová chyba interpretace – chybná práce s řetězcem.
"""
import sys
import xml.etree.ElementTree as XML
import argparse
import re

INSTRUCTIONS = ['CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'RETURN', 'BREAK', 'DEFVAR', 'CALL', 'PUSHS', 'POPS', 'WRITE',
                'LABEL', 'JUMP', 'EXIT', 'DPRINT', 'READ', 'STRLEN', 'TYPE', 'MOVE', 'NOT', 'INT2CHAR', 'ADD', 'SUB',
                'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'STRI2INT', 'CONCAT', 'GETCHAR', 'SETCHAR', 'JUMPIFEQ',
                'JUMPIFNEQ']
NO_OP_INSTRUCTIONS = ['CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'RETURN', 'BREAK']
ONE_OP_INSTRUCTIONS = ['DEFVAR', 'CALL', 'PUSHS', 'POPS', 'WRITE', 'LABEL', 'JUMP', 'EXIT', 'DPRINT']
TWO_OP_INSTRUCTIONS = ['READ', 'STRLEN', 'TYPE', 'MOVE', 'NOT', 'INT2CHAR']
THREE_OP_INSTRUCTIONS = ['ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'STRI2INT', 'CONCAT', 'GETCHAR',
                         'SETCHAR', 'JUMPIFEQ', 'JUMPIFNEQ']

INT_INSTRUCTIONS = ['ADD', 'SUB', 'MUL', 'IDIV']


class ErrorHandler:
    """
    Class used for handling errors and exits

    Methods
    -------
    Class containts one static method for print message and exit with error code
    """
    RUN_ERR_MISSING_PARAM = 10
    RUN_ERR_INFILE_OPEN = 11
    RUN_ERR_OUTFILE_OPEN = 12
    ERROR_WRONG_XML_INPUT_FORMAT = 31
    ERROR_UNEXPECTED_XML_STRUCT = 32
    ERROR_SEMANTIC_XML_INPUT = 52
    ERROR_INVALID_OP = 53
    ERROR_VAR_NOT_EXIST = 54
    ERROR_INVALID_FRAME = 55
    ERROR_MISSING_VALUE = 56
    ERROR_WRONG_OP_VALUE = 57
    ERROR_WRONG_STRING_OPERATION = 58
    GENERAL_ERR = 99

    @staticmethod
    def exit_with_message(msg, err_code):
        print(msg, file=sys.stderr)
        sys.exit(err_code)


class DataStore:
    """
    Class contains all data that interpreter uses

    Attributes
    -------
    Described after each attr.

    Methods
    -------
    None
    """
    _instructions = {}      # stored all incoming instructions
    _defined_labels = {}    # store all labels and order of that labels
    _GF = {}                # Global frame storage
    _LF = []                # Local frame storage
    _TF = None              # Temp frame storage
    _data_stack = []        # Data stack
    _call_stack = []        # Call stack
    _arg1_temp_val = None   # Fist, second and third operand after command, set in each instruction
    _arg2_temp_val = None
    _arg3_temp_val = None
    read_source = None      # Defines from where will get input
    is_file = None          # If not file, still None, if file set fopen
    _skip_until = 0         # To which order will interpret skip if label is before call
    _reset_interpret = False    # Helper for skip until
    _order_count = 0


class ParseXML(DataStore):
    """
    Class for parse incoming xml and fill _instructions and _defined_labels in DataStore
    """
    __xml_origin = None
    __xml_root = None
    __instructions = {}
    __defined_labels = {}
    __DS = None

    def __init__(self, xml_source, read_source, file=None):
        self.__DS = DataStore
        self.__DS.read_source = read_source
        self.__DS.is_file = file
        try:
            self.__xml_origin = XML.parse(xml_source)
            self.__xml_root = self.__xml_origin.getroot()
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(ErrorHandler.ERROR_WRONG_XML_INPUT_FORMAT)

    @staticmethod
    def _validate_arg(arg):
        types = ["int", "bool", "string", "nil", "label", "type", "var"]
        tags = ["arg1", "arg2", "arg3"]
        if arg.attrib.get('type') is None or arg.attrib['type'] not in types or arg.tag not in tags:
            ErrorHandler.exit_with_message("Invalid arg type or tag name", ErrorHandler.ERROR_UNEXPECTED_XML_STRUCT)

    @staticmethod
    def _find_num_args(opcode):
        if opcode in NO_OP_INSTRUCTIONS:
            return 0
        elif opcode in ONE_OP_INSTRUCTIONS:
            return 1
        elif opcode in TWO_OP_INSTRUCTIONS:
            return 2
        elif opcode in THREE_OP_INSTRUCTIONS:
            return 3
        else:
            ErrorHandler.exit_with_message("_find_num_args: opcode not found in arrays", ErrorHandler.GENERAL_ERR)

    def parse_instructions(self):
        try:
            if \
                    self.__xml_root.tag != 'program' or \
                            'language' not in self.__xml_root.attrib or \
                            self.__xml_root.attrib['language'] != 'IPPcode23':
                raise XML.ParseError("Invalid source language")

            for child in self.__xml_root:
                if child.tag != 'instruction':
                    raise XML.ParseError('Not instruction tag')

                order = int(child.attrib['order'])
                child.attrib['order'] = int(child.attrib['order'])

                if order < 1:
                    raise XML.ParseError("Order cannot be less then 1")
                opcode = child.attrib['opcode']

                # check if exists
                if opcode not in INSTRUCTIONS:
                    raise XML.ParseError("opcode not instruction " + str(opcode))

                # add instruction to final struct
                final_instruction = child.attrib

                args = {}
                for arg in child:
                    # run validation
                    self._validate_arg(arg)

                    # check if not duplicate arg
                    if final_instruction.get(arg.tag) is None:
                        # print(str(arg.attrib), str(arg.attrib) == 'string')
                        if arg.text is None and arg.attrib['type'] != 'string':
                            ErrorHandler.exit_with_message("Invalid arg", ErrorHandler.ERROR_UNEXPECTED_XML_STRUCT)
                        if arg.text is None and arg.attrib['type'] == 'string':
                            arg.attrib['text'] = ""
                        else:
                            arg.attrib['text'] = arg.text
                        # final_instruction[arg.tag] = arg.attrib
                        args[arg.tag] = arg.attrib
                    else:
                        ErrorHandler.exit_with_message("Duplicite arg found", ErrorHandler.GENERAL_ERR)

                testArg = []
                for i in args:
                    testArg.append(i)
                if ('arg2' in testArg and 'arg1' not in testArg) or ('arg3' in testArg and 'arg2' not in testArg):
                    raise XML.ParseError("Wrong arg number")

                # check if it's right number of arguments
                if len(args) != self._find_num_args(opcode):
                    raise XML.ParseError("Invalid number of args for this functions")

                args = dict(sorted(args.items(), key=lambda x: x))
                final_instruction['args'] = args

                # save labels
                if opcode == 'LABEL':
                    if final_instruction['args']["arg1"]['text'] in self.__defined_labels:
                        sys.exit(ErrorHandler.ERROR_SEMANTIC_XML_INPUT)
                    self.__defined_labels[final_instruction['args']["arg1"]['text']] = final_instruction

                if order in self.__instructions:
                    raise XML.ParseError('Double order detected')

                self.__instructions[order] = final_instruction

        except Exception as e:
            ErrorHandler.exit_with_message("Parse err: " + str(e), ErrorHandler.ERROR_UNEXPECTED_XML_STRUCT)

        # sort array of instructions and return
        self.__DS._instructions = dict(sorted(self.__instructions.items(), key=lambda x: x))
        self.__DS._defined_labels = self.__defined_labels


class ValidateArguments:
    """
    Class contains only static methods for validating input and return escaped strings
    """

    @staticmethod
    def is_var(arg, exit=False):
        if arg['type'] == 'var' and bool(re.match(r'(GF|TF|LF)@[a-zA-Z_$-%!&?*][a-zA-Z_$-%!&?*0-9]*', arg['text'])):
            return True
        else:
            if exit:
                ErrorHandler.exit_with_message("Invalid arg not var" + str(arg), ErrorHandler.ERROR_INVALID_OP)
            else:
                return False

    @staticmethod
    def is_const(arg, exit=False):
        types = ['nil', 'bool', 'string', 'int']
        # print('is_const',arg)
        if arg['type'] in types and type(arg['text']) == int:
            return True
        elif arg['type'] in types and bool(re.match(r'[a-zA_$-%!?*0-9]*', arg['text'])):
            return True
        else:
            if exit:
                ErrorHandler.exit_with_message("Invalid arg not const" + str(arg), ErrorHandler.ERROR_INVALID_OP)
            else:
                return False

    @staticmethod
    def escape_string(text):
        # print(type(text) == bool)
        if type(text) == bool:
            if text:
                text = 'true'
            else:
                text = 'false'
        starting_index = 0
        while text.find('\\', starting_index) != -1:
            i = text.find('\\', starting_index)
            char = text[i + 1:i + 4]
            # if bool(re.match(r'^[0-9][0-9][0-9]$', char)):
            if char != '':
                text = text[:i] + chr(int(char)) + text[i + 4:]
                starting_index = i
            else:
                text = text[:i] + text[i] + text[i + 4:]
                starting_index = i + 1
        return text


class InterpretWorker(DataStore):
    """
    Main class for interpret uses start_interpret for run and functions for each instruction
    """

    def __init__(self):
        pass

    def start_interpreter(self):
        """
        Main function for interpret
        :return:
        """
        # starts while cycle with break, but if I have to jump to earlier instruction i break for and restart it
        # with while to reach that label
        break_while = False
        while True:
            for i in self._instructions:
                self._order_count = i

                if self._skip_until > i:
                    continue
                if self._reset_interpret:
                    break
                self._execute_instruction(self._instructions[int(i)])

            # breaks while
            if self._reset_interpret:
                self._reset_interpret = False
            else:
                break

    def __insert_to_frame(self, name, data, update=False):
        """
        Check if frame exists and if updating, also if variable exists
        :param name: name of var
        :param data: data to var
        :param update: insert new/update existing
        :return:
        """
        name = name.split('@')
        frame = name[0]
        name = name[1]

        if frame == 'LF':
            if not self._LF:
                ErrorHandler.exit_with_message("Frame not initialized", ErrorHandler.ERROR_INVALID_FRAME)

            if update and name not in self._LF[-1]:
                ErrorHandler.exit_with_message("check and insert err", ErrorHandler.ERROR_VAR_NOT_EXIST)

            if not update and name in self._LF[-1]:
                ErrorHandler.exit_with_message("Try to redefine err", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)
            self._LF[-1][name] = data
        elif frame == 'GF':
            if update and name not in self._GF:
                ErrorHandler.exit_with_message("check and insert err", ErrorHandler.ERROR_VAR_NOT_EXIST)

            if not update and name in self._GF:
                ErrorHandler.exit_with_message("Try to redefine err", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)

            self._GF[name] = data
        elif frame == 'TF':
            if self._TF is None:
                ErrorHandler.exit_with_message("Frame not initialized", ErrorHandler.ERROR_INVALID_FRAME)

            if update and name not in self._TF:
                ErrorHandler.exit_with_message("check and insert err", ErrorHandler.ERROR_VAR_NOT_EXIST)

            if not update and name in self._TF:
                ErrorHandler.exit_with_message("Try to redefine err", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)
            self._TF[name] = data

    def __get_var_from_frame(self, name, instruction):
        """
        Method for get data from frames
        :param name: name of variable
        :param instruction: instruction data
        :return:
        """
        name = name.split('@')
        frame = name[0]
        name = name[1]

        try:
            if frame == 'LF' and self._LF == []:
                ErrorHandler.exit_with_message("Frame not initialized", ErrorHandler.ERROR_INVALID_FRAME)
            if frame == 'LF' and name in self._LF[-1]:
                if self._LF[-1][name]['text'] is None and instruction['opcode'] != 'TYPE':
                    raise Exception('var does not exists')
                return self._LF[-1][name]
            elif frame == 'GF' and name in self._GF:
                if self._GF[name]['text'] is None and instruction['opcode'] != 'TYPE':
                    raise Exception('var does not exists')
                return self._GF[name]
            elif frame == 'TF':
                if self._TF is None:
                    ErrorHandler.exit_with_message("Frame not initialized", ErrorHandler.ERROR_INVALID_FRAME)
                if name in self._TF:
                    if self._TF[name]['text'] is None and instruction['opcode'] != 'TYPE':
                        raise Exception('var does not exists')
                    return self._TF[name]
                else:
                    ErrorHandler.exit_with_message("get val err not defined: " + name, ErrorHandler.ERROR_VAR_NOT_EXIST)
            else:
                ErrorHandler.exit_with_message("get val err not defined: " + name, ErrorHandler.ERROR_VAR_NOT_EXIST)
        except Exception as e:
            ErrorHandler.exit_with_message("get_var_from_frame err: " + frame + '@' + name + str(e),
                                           ErrorHandler.ERROR_MISSING_VALUE)

    """
    Here starts all methods for each instruction
    """
    def _move(self, instruction):
        self.__insert_to_frame(self._arg1_temp_val['text'], self._arg2_temp_val, True)

    def _createframe(self, instruction):
        self._TF = {}

    def _pushframe(self, instruction):
        if self._TF is None:
            ErrorHandler.exit_with_message("Trying to push empty", ErrorHandler.ERROR_INVALID_FRAME)
        else:
            self._LF.append(self._TF)
            self._TF = None

    def _popframe(self, instruction):
        if self._LF:
            self._TF = self._LF.pop()
        else:
            ErrorHandler.exit_with_message("Unable to pop frame doesn't exits", ErrorHandler.ERROR_INVALID_FRAME)

    def _defvar(self, instruction):
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': self._arg1_temp_val['type'], 'text': None})

    def _call(self, instruction):
        call = {'order': self._order_count}
        self._call_stack.append(call)
        self._jump(instruction)

    def _return(self, instruction):
        if not self._call_stack:
            ErrorHandler.exit_with_message("Empty call stack unable to return", ErrorHandler.ERROR_MISSING_VALUE)
        call = self._call_stack.pop()
        self._skip_until = int(call['order']) + 1
        if self._skip_until <= self._order_count:
            self._reset_interpret = True

    def _pushs(self, instruction):
        self._data_stack.append(self._arg1_temp_val)

    def _pops(self, instruction):
        if not self._data_stack:
            ErrorHandler.exit_with_message("empty stack", ErrorHandler.ERROR_MISSING_VALUE)
        result = self._data_stack.pop()
        self.__insert_to_frame(self._arg1_temp_val['text'], result, True)

    def _add(self, instruction):
        result = self._arg2_temp_val['text'] + self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': int(result)}, True)

    def _sub(self, instruction):
        result = self._arg2_temp_val['text'] - self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': int(result)}, True)

    def _mul(self, instruction):
        result = self._arg2_temp_val['text'] * self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': int(result)}, True)

    def _idiv(self, instruction):
        if int(self._arg3_temp_val['text']) == 0:
            ErrorHandler.exit_with_message('Divide by zero', ErrorHandler.ERROR_WRONG_OP_VALUE)
        result = self._arg2_temp_val['text'] / self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': int(result)}, True)

    def _lt(self, instruction):
        result = self._arg2_temp_val['text'] < self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _gt(self, instruction):
        result = self._arg2_temp_val['text'] > self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _eq(self, instruction):
        result = self._arg2_temp_val['text'] == self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _and(self, instruction):
        result = self._arg2_temp_val['text'] and self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _or(self, instruction):
        result = self._arg2_temp_val['text'] or self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _not(self, instruction):
        result = not self._arg2_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': str(result).lower()}, True)

    def _int2char(self, instruction):
        try:
            result = chr(self._arg2_temp_val['text'])
            self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'string', 'text': result}, True)
        except Exception as e:
            ErrorHandler.exit_with_message('Invalid op: ' + str(e), ErrorHandler.ERROR_WRONG_STRING_OPERATION)

    def _stri2int(self, instruction):
        try:
            if 0 > self._arg3_temp_val['text'] or self._arg3_temp_val['text'] >= len(self._arg2_temp_val['text']) or \
                    self._arg2_temp_val['text'] == '':
                raise Exception('out of range')
            result = ord(self._arg2_temp_val['text'][self._arg3_temp_val['text']])
        except Exception as err:
            ErrorHandler.exit_with_message('Invalid arr index: ' + str(err),
                                           ErrorHandler.ERROR_WRONG_STRING_OPERATION)
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': result}, True)

    def _read(self, instruction):
        if self._arg2_temp_val['type'] != 'type':
            ErrorHandler.exit_with_message('cannot print nil or not type', ErrorHandler.ERROR_UNEXPECTED_XML_STRUCT)
        if self._arg2_temp_val['text'] == 'nil':
            ErrorHandler.exit_with_message('cannot print nil or not type', ErrorHandler.ERROR_INVALID_OP)
        type = self._arg2_temp_val['text']

        empty = True
        try:
            if self.is_file is not None:
                src = self.is_file.readline()
                if len(src) != 0:
                    empty = False

            else:
                src = input()
        except:
            src = 'nil'

        src = src.strip()
        is_digit = True
        try:
            in_len = len(src)
            src = int(src)
        except:
            is_digit = False

        if type == 'int' and is_digit:
            self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': int(src)}, True)

        elif type == 'bool' and src != '':
            if src.lower() == 'true':
                self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': 'true'}, True)
            else:
                self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'bool', 'text': 'false'}, True)

        elif type == 'string' and src != 'nil' and not empty:
            self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'string', 'text': src}, True)

        else:
            self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'nil', 'text': 'nil'}, True)

    def _write(self, instruction):
        if self._arg1_temp_val['type'] == 'nil':
            text = ''
        else:
            text = self._arg1_temp_val['text']

        # handle escapes
        if type(text) != int:
            text = ValidateArguments.escape_string(text)

        print(text, end="")

    def _concat(self, instruction):
        result = self._arg2_temp_val['text'] + self._arg3_temp_val['text']
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'string', 'text': result}, True)

    def _strlen(self, instruction):
        result = len(self._arg2_temp_val['text'])
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'int', 'text': result}, True)

    def _getchar(self, instruction):
        try:
            if 0 > self._arg3_temp_val['text'] or len(self._arg2_temp_val['text']) <= self._arg3_temp_val['text']:
                raise Exception("out of range")
            result = self._arg2_temp_val['text'][self._arg3_temp_val['text']]
        except Exception as e:
            ErrorHandler.exit_with_message(str(e), ErrorHandler.ERROR_WRONG_STRING_OPERATION)
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'string', 'text': result}, True)

    def _setchar(self, instruction):
        try:
            result = self.__get_var_from_frame(self._arg1_temp_val['text'], instruction)

            if 0 > self._arg2_temp_val['text'] or self._arg2_temp_val['text'] >= len(result['text']) or \
                    self._arg3_temp_val['text'] == '':
                ErrorHandler.exit_with_message("out of string", ErrorHandler.ERROR_WRONG_STRING_OPERATION)

            if result['type'] != 'string':
                raise Exception("invalid setchar type")

            result = result['text']
            result = f"{result[:self._arg2_temp_val['text']]}{self._arg3_temp_val['text'][0]}{result[self._arg2_temp_val['text'] + 1:]}"
        except Exception as e:
            ErrorHandler.exit_with_message('ERR : ' + str(e), ErrorHandler.ERROR_INVALID_OP)
        self.__insert_to_frame(self._arg1_temp_val['text'], {'type': 'string', 'text': result}, True)

    def _type(self, instruction):

        if self._arg2_temp_val['type'] == 'type':
            self.__insert_to_frame(self._arg1_temp_val['text'],
                                   {'type': 'type', 'text': 'string'}, True)

        elif self._arg2_temp_val['text'] is None and self._arg2_temp_val['type'] == 'var':
            self.__insert_to_frame(self._arg1_temp_val['text'],
                                   {'type': 'type', 'text': ''}, True)
        else:
            self.__insert_to_frame(self._arg1_temp_val['text'],
                                   {'type': 'type', 'text': self._arg2_temp_val['type']}, True)

    def _label(self, instruction):
        return

    def _jump(self, instruction):
        if self._arg1_temp_val['text'] not in self._defined_labels:
            ErrorHandler.exit_with_message("Label not found", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)

        self._skip_until = int(self._defined_labels[self._arg1_temp_val['text']]['order'])
        if self._skip_until < self._order_count:
            self._reset_interpret = True

    def _jumpifeq(self, instruction):
        if self._arg1_temp_val['text'] not in self._defined_labels:
            ErrorHandler.exit_with_message("Label not found", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)

        if self._arg2_temp_val['text'] == self._arg3_temp_val['text']:
            self._skip_until = int(self._defined_labels[self._arg1_temp_val['text']]['order'])
            if self._skip_until < self._order_count:
                self._reset_interpret = True

    def _jumpifneq(self, instruction):
        if self._arg1_temp_val['text'] not in self._defined_labels:
            ErrorHandler.exit_with_message("Label not found", ErrorHandler.ERROR_SEMANTIC_XML_INPUT)

        if self._arg2_temp_val['text'] != self._arg3_temp_val['text']:
            self._skip_until = int(self._defined_labels[self._arg1_temp_val['text']]['order'])
            if self._skip_until < self._order_count:
                self._reset_interpret = True

    def _exit(self, instruction):
        exit_code = self._arg1_temp_val['text']
        try:
            if 0 <= exit_code < 50:
                sys.exit(exit_code)
            else:
                ErrorHandler.exit_with_message("failed to exit invalid err code: " + str(exit_code),
                                               ErrorHandler.ERROR_WRONG_OP_VALUE)
        except Exception as e:
            ErrorHandler.exit_with_message("failed to exit convert err: " + str(e), ErrorHandler.ERROR_INVALID_OP)

    def _dprint(self, instruction):
        pass

    def _break(self, instruction):
        pass

    def _execute_instruction(self, instruction):
        """
        Method called from start_interpret check data, get data from frame and execute instruction
        :param instruction:
        :return:
        """

        # reset data store
        self._arg1_temp_val = self._arg2_temp_val = self._arg3_temp_val = None

        # iterate over arguments and set data to DataStore
        for arg, arg_data in instruction['args'].items():
            if ValidateArguments.is_const(arg_data):
                # if type should be int, try to convert
                if arg_data['type'] == 'int':
                    try:
                        arg_data['text'] = int(arg_data['text'])
                    except Exception as e:
                        ErrorHandler.exit_with_message("Execute unable to convert to int" + str(e),
                                                       ErrorHandler.ERROR_SEMANTIC_XML_INPUT)
                # if bool try to match
                elif arg_data['type'] == 'bool':
                    if arg_data['text'] == 'true':
                        arg_data['text'] = True
                    elif arg_data['text'] == 'false':
                        arg_data['text'] = False
                    else:
                        ErrorHandler.exit_with_message("not boolean", ErrorHandler.ERROR_INVALID_OP)
                # if it's string, check if it contains escaped string to replace
                elif arg_data['type'] == 'string':
                    arg_data['text'] = ValidateArguments.escape_string(arg_data['text'])
                # check nil type
                if arg_data['type'] == 'nil' and arg_data['text'] != 'nil':
                    ErrorHandler.exit_with_message("not boolean", ErrorHandler.ERROR_INVALID_OP)

            # Get data from variable if var not supposed to be written
            if (ValidateArguments.is_var(arg_data) and arg in ('arg2', 'arg3')) or \
                    (instruction['opcode'] in ('WRITE', 'EXIT', 'PUSHS') and ValidateArguments.is_var(arg_data)):
                arg_data = self.__get_var_from_frame(arg_data['text'], instruction)

            # save data to DataStore
            if arg == 'arg1':
                self._arg1_temp_val = arg_data
            elif arg == 'arg2':
                self._arg2_temp_val = arg_data
            else:
                self._arg3_temp_val = arg_data

        # Check args specific for these instructions
        if instruction['opcode'] in ('EXIT') and self._arg1_temp_val['type'] != 'int':
            ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if (instruction['opcode'] in ('AND', 'OR') and
            (self._arg2_temp_val['type'] != 'bool' or self._arg3_temp_val['type'] != 'bool')) or \
                instruction['opcode'] == 'NOT' and self._arg2_temp_val['type'] != 'bool':
            ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('ADD', 'SUB', 'IDIV', 'MUL') and \
                (self._arg2_temp_val['type'] != 'int' or self._arg3_temp_val['type'] != 'int'):
            ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('CONCAT') and \
                (self._arg2_temp_val['type'] != 'string' or self._arg3_temp_val['type'] != 'string'):
            ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('SETCHAR'):
            if self._arg2_temp_val['type'] != 'int' or self._arg3_temp_val['type'] != 'string':
                ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('INT2CHAR'):
            if self._arg2_temp_val['type'] != 'int':
                ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('STRLEN'):
            if self._arg2_temp_val['type'] != 'string':
                ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('GETCHAR', 'STRI2INT'):
            if self._arg2_temp_val['type'] != 'string' or self._arg3_temp_val['type'] != 'int':
                ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('LT', 'GT'):
            if self._arg2_temp_val['type'] != self._arg3_temp_val['type'] or \
                    (self._arg2_temp_val['type'] == 'nil' or self._arg3_temp_val['type'] == 'nil'):
                ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        if instruction['opcode'] in ('EQ', 'JUMPIFEQ', 'JUMPIFNEQ') and \
                self._arg2_temp_val['type'] != self._arg3_temp_val['type'] and \
                (self._arg2_temp_val['type'] != 'nil' and self._arg3_temp_val['type'] != 'nil'):
            ErrorHandler.exit_with_message("Add invalid op ", ErrorHandler.ERROR_INVALID_OP)

        # Dynamically call function
        string_name = "_" + instruction['opcode'].lower()
        func = getattr(self, string_name)
        func(instruction)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--source")
    parser.add_argument("--input")

    args = parser.parse_args()
    if args.source is None and args.input is None:
        ErrorHandler.exit_with_message("Use at least --source or --input", ErrorHandler.RUN_ERR_MISSING_PARAM)

    if args.source is None:
        args.source = sys.stdin

    if args.input is None:
        args.input = sys.stdin
        xml_parser = ParseXML(args.source, args.input)
    else:
        file = open(args.input, "r")
        xml_parser = ParseXML(args.source, None, file)

    xml_parser.parse_instructions()

    interpret = InterpretWorker()
    interpret.start_interpreter()


if __name__ == "__main__":
    main()
