<?php

const noOP = ['CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'RETURN', 'BREAK'];
const oneOP = ['DEFVAR', 'CALL', 'PUSHS', 'POPS', 'WRITE', 'LABEL', 'JUMP', 'EXIT', 'DPRINT'];
const twoOP = ['READ', 'STRLEN', 'TYPE', 'MOVE', 'NOT', 'INT2CHAR'];
const threeOP = ['ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'STRI2INT', 'CONCAT', 'GETCHAR', 'SETCHAR', 'JUMPIFEQ', 'JUMPIFNEQ'];

// ONE OP FUNCTUINS
const oneOPvar = ['DEFVAR', 'POPS'];
const oneOPlabel = ['CALL', 'LABEL', 'JUMP'];
const oneOPsymbol = ['PUSHS', 'WRITE', 'EXIT', 'DPRINT'];

const HEADER_MISSING_ERR = 21;
const OPCODE_ERR = 22;
const LEXSYN_ERR = 23;

// Line read from src file
$line = 0;

//check if header declared
$headerFound = false;

//line number
$lineNum = 0;

//order of OP
$order = 0;

//Array for instructions
$instruction = null;

//Create new DOMDocument for XML
$DOM = new DOMDocument('1.0', 'UTF-8');
$DOM->formatOutput = true;

//Create header and prog root element
$XMLHead = $DOM->createElement('program');
$XMLHead->setAttribute('language', 'IPPcode23');
$DOM->appendChild($XMLHead);