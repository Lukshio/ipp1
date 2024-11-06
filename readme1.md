# Implementační dokumentace k projektu do IPP 2022/23
### Jméno a příjmení: Lukáš Ježek
### Login: xjezek19

## Parse.php
Script parse.php je dle zadání naprogramován v jazyce PHP 8.1.  
Program se skládá ze souboru `parse.php` a `init.php`, který slouží pro deklaraci a definici globálních proměnných.  
V souboru `init.php` jsou nadefinována pole s názvy funkcí rozdělené podle počtu operandů. Dále nadeklarována globální proměnná `$DOM` a `$XMLHead`, obě jsou formátu `DOMDocument`
pro generování XML dokumentu. `$DOM` slouží jako instance `DOMDocument`, `$XMLHead` potom slouží pro přidávání potomků kořenovému elementu `<program>`.  

Program `parse.php` čte zdrojový kód jazyka `IPPcode23` ze standardního vstupu, výstupem je potom XML dokument, který je vypsán na standardní výstup. Chybová hlášení jsou vypisována na výstup `stderr`. Program používá striktní typování `declare(strict_types=1)`.  
Program čte vstup po řádku, každý řádek je poté rozdělen pomocí mezer do pole. Následně jsou odstraněny nadbytečné mezery, tabulátory a značky nového řádku, také pokud řádek začíná `#` je automaticky odstraněn, jelikož se jedná o komentář. 
Na takto upravené pole se zavolá funkce `deleteComment($array)`, která najde a odstraní inline komentáře.
Program následně kontroluje, jestli byla deklarována povinná hlavička programu a zároveň, že se nejedná o jeji redeklaraci.
Poté se očekávaná instrukce převede na uppercase a pomocí rozhodovacího bloku se zavolá příslušná funkce obsluhující daný počet operandů, pokud instrukce neexistuje, program končí chybou 22.
Implementovány jsou pomocné funkce `argFactory($num, $content, $type)` - vytváření objektu pro funkci `insertInstruction($instruction, $args)`. Dále `checkOperands($operand, $compare)`, která kontroluje jestli je daný operand očekavaným pro danou instrukci a`escapeString($string)` pro escapování stringů a escape sekvence  