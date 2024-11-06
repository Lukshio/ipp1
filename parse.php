<?php
declare(strict_types=1);
ini_set('display_errors', 'stderr');

require_once 'init.php';

global $DOM, $headerFound, $lineNum;

if ($argc == 2 && $argv[1] == '--help') {
    echo "Run script using php8.1 parse.php < sourcefile \n";
    exit(0);
} elseif (in_array('--help', $argv) && $argc > 2){
    exit(10);
}

while ($line = fgets(STDIN)) {
    $instruction = (explode(' ', $line));

    //remove whitespaces from array and reindex array
    foreach ($instruction as $key => $item) {
        if (empty($item)) unset($instruction[$key]);
    }
    $instruction = array_values($instruction);

    // check if it's not space even after removed whitespaces
    if (ctype_space($instruction[0])) continue;

    // check if whole line isn't comment
    if (str_starts_with($instruction[0], '#')) continue;

    //remove tabs,spaces,newlines...
    for ($i = 0; $i < count($instruction); $i++) {
        $instruction[$i] = trim($instruction[$i]);
    }

    //remove comments from array
    $instruction = deleteComments($instruction);

    //catch duplicate header
    if ($headerFound && $instruction[0] == '.IPPcode23') exit(OPCODE_ERR);

    //check if header exists
    if (!$headerFound && $instruction[0] != '.IPPcode23') exit(HEADER_MISSING_ERR);
    elseif (!$headerFound && $lineNum == 0) {
        $headerFound = true;
        continue;
    }

    $instruction[0] = (strtoupper($instruction[0]));
    $lineNum++;

    // try block for catch DOMException, by name find correct function and check num of operands
    try {
        if (!in_array($instruction[0], noOP) &&
            !in_array($instruction[0], oneOP) &&
            !in_array($instruction[0], twoOP) &&
            !in_array($instruction[0], threeOP))
            exit(OPCODE_ERR);

        if (in_array($instruction[0], noOP) && count($instruction) == 1) noOPInstructions($instruction);
        elseif (in_array($instruction[0], oneOP) && count($instruction) == 2) oneOPInstruction($instruction);
        elseif (in_array($instruction[0], twoOP) && count($instruction) == 3) twoOPInstruction($instruction);
        elseif (in_array($instruction[0], threeOP) && count($instruction) == 4) threeOPInstruction($instruction);
        else exit(LEXSYN_ERR);

    } catch (DOMException $exception) {
        var_dump($exception);
        exit(LEXSYN_ERR);
    }
}

echo $DOM->saveXML();


/**
 * Function deletes comments from given string array
 * @param $instructions
 * @return mixed
 */
function deleteComments($instructions): mixed
{
    foreach ($instructions as $key => $item) {
        if (str_contains($item, '#')) {
            $exploded = (explode('#', $item));
            if (array_key_exists(($key + 1), $instructions)) (array_splice($instructions, $key));
            if (empty($exploded[0])) unset($instructions[$key]);
            else $instructions[$key] = $exploded[0];
            break;
        }
    }
    return $instructions;
}

/**
 * Function handeling no operands instructions
 * @param $instruction
 * @return void
 * @throws DOMException
 */
function noOPInstructions($instruction): void
{
    if ($instruction[0] == null) exit(LEXSYN_ERR);
    insertInstruction($instruction[0], []);
}

/**
 * Function handeling 1 operand instructions
 * @param $instruction
 * @return void
 * @throws DOMException
 */
function oneOPInstruction($instruction): void
{
    if (in_array($instruction[0], oneOPvar) && checkOperands($instruction[1], 'var')) {
        insertInstruction($instruction[0], [argFactory(1, $instruction[1], 'var')]);

    } else if (in_array($instruction[0], oneOPlabel) && checkOperands($instruction[1], 'label')) {
        insertInstruction($instruction[0], [argFactory(1, $instruction[1], 'label')]);

    } else if (in_array($instruction[0], oneOPsymbol) && $symbol = checkOperands($instruction[1], 'symbol')) {
        insertInstruction($instruction[0], [argFactory(1, $symbol->content, $symbol->type)]);

    } else exit(LEXSYN_ERR);
}

/**
 * Function handeling 2 operands instructions
 * @param $instruction
 * @return void
 * @throws DOMException
 */
function twoOPInstruction($instruction): void
{
    if (checkOperands($instruction[1], 'var')) $arg1 = argFactory(1, $instruction[1], 'var');
    else exit(LEXSYN_ERR);

    if ($instruction[0] == 'READ') {
        if (checkOperands($instruction[2], 'type')) $arg2 = argFactory('2', $instruction[2], 'type');
        else exit(LEXSYN_ERR);

    } else {
        $symbol = checkOperands($instruction[2], 'symbol');
        $arg2 = argFactory('2', $symbol->content, $symbol->type);
    }
    insertInstruction($instruction[0], [$arg1, $arg2]);
}

/**
 * Function handeling 3 operands instructions
 * @param $instruction
 * @return void
 * @throws DOMException
 */
function threeOPInstruction($instruction): void
{
    if (($instruction[0] === 'JUMPIFEQ' || $instruction[0] === 'JUMPIFNEQ')){
        if (checkOperands($instruction[1], 'label'))$arg1 = argFactory(1, $instruction[1], 'label');
        else exit(LEXSYN_ERR);
    }
    elseif (checkOperands($instruction[1], 'var')) $arg1 = argFactory(1, $instruction[1], 'var');
    else exit(LEXSYN_ERR);

    $symbol1 = checkOperands($instruction[2], 'symbol');
    $symbol2 = checkOperands($instruction[3], 'symbol');
    $arg2 = argFactory(2, $symbol1->content, $symbol1->type);
    $arg3 = argFactory(3, $symbol2->content, $symbol2->type);

    insertInstruction($instruction[0], [$arg1, $arg2, $arg3]);
}

/**
 * Function creates and returns object from function params
 * @param $num
 * @param $content
 * @param $type
 * @return object
 */
function argFactory($num, $content, $type): object
{
    if ($type == 'var') $content = escapeString($content);
    return (object)[
        'num' => $num,
        'content' => $content,
        'type' => $type
    ];
}

/**
 * Function creates new XML tags with attributtes passed in $arg
 * @param $instruction
 * @param $args
 * @return void
 * @throws DOMException
 */
function insertInstruction($instruction, $args): void
{
    global $DOM, $lineNum, $XMLHead;
    $XMLInstruction = $DOM->createElement('instruction');
    $XMLInstruction->setAttribute('order', (string)$lineNum);
    $XMLInstruction->setAttribute('opcode', $instruction);
    foreach ($args as $arg) {
        $child = $DOM->createElement('arg' . $arg->num, $arg->content);
        $child->setAttribute('type', $arg->type);
        $XMLInstruction->appendChild($child);
    }
    $XMLHead->appendChild($XMLInstruction);
}

/**
 * Funkce kontroluje operandy, v pripade kontroly const,var,label,type vraci true/false,
 * v pripade symbol vraci (objekt) ['type' => typ, 'content' => content];
 * @param $operand
 * @param $compare
 * @return bool|object|void
 */
function checkOperands($operand, $compare)
{
    switch ($compare) {
        case 'const':
            return (bool)preg_match('/(nil|bool|string|int)@[a-zA_$-%!?*0-9]*/', $operand);

        case 'var':
            return (bool)preg_match('/(GF|TF|LF)@[a-zA-Z_$-%!&?*][a-zA-Z_$-%!&?*0-9]*/', $operand);

        case 'symbol':
            if (checkOperands($operand, 'var')) {
                return (object)['type' => 'var', 'content' => $operand];
            } elseif (checkOperands($operand, 'const')) {
                $parsed = explode('@', $operand, 2);
                if ($parsed[0] != 'string' && $parsed[1] == '' ||
                    $parsed[0] == 'nil' && $parsed[1] != 'nil' ||
                    $parsed[0] == 'bool' && ($parsed[1]) != 'true' && $parsed[1] != 'false'
                ) exit(LEXSYN_ERR);
                if ($parsed[0] == 'string') $parsed[1] = escapeString($parsed[1]);

                return (object)['type' => $parsed[0], 'content' => $parsed[1]];

            } else exit(LEXSYN_ERR);

        case 'label':
            return (bool)preg_match('/^-*[a-zA-Z_$-%!?*][a-zA-Z_$-%!?*0-9]*$/', $operand);

        case 'type':
            return (bool)preg_match('/^(nil|bool|string|int)$/', $operand);
    }
    exit(OPCODE_ERR);
}

/**
 * Escapes <,>,& and chars with dec value starting with \000
 * @param $string
 * @return array|mixed|string|string[]|void
 */
function escapeString($string)
{
    if (str_contains($string, "\\")) {
        $parse = explode('\\', $string);
        for ($i = 1; $i < count($parse); $i++) {
            if (preg_match('/[0-9][0-9][0-9][a-zA-Z0-9]*/', $parse[$i])) continue;
            else exit(LEXSYN_ERR);
        }
    }
    if (str_contains($string, '&')) $string = str_replace('&', '&amp;', $string);
    if (str_contains($string, '<')) $string = str_replace('&', '&lt;', $string);
    if (str_contains($string, '>')) $string = str_replace('&', '&gt;', $string);
    return $string;
}