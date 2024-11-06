# Implementační dokumentace k projektu do IPP 2022/23
### Jméno a příjmení: Lukáš Ježek
### Login: xjezek19

## interpret.py
Script interpret.py je dle zadání naprogramován v jazyce Python 3.10  
Program se skládá z jednoho souboru `interpret.py`.    

#### Třídy a metody
Program obsahuje několik tříd a metod. Třída `ErrorHandler` má v sobě nadefinované typy chyb a k nim příslušný exit kód. Obsahuje statickou metodu `exit_with_message`, která se používá k výpisu chyby na `stderr` a poté ukončí program kódem z parametru.

Třída `DataStore` slouží k uchování a sdílení dat mezi třídami které z této třídy dědí, ke každé položce je v kódu uveden popis.


Třída `ParseXML(DataStore)` má za úkol ze vstupního XML formátu vybrat instrukce a jejich operandy. Provádí také první vstupní kontrolu instrukcí a operandů. Vše je vkládáno do třídy `DataStore`. Instrukce jsou vkládany do `_instructions`, návěští do `_defined_labels`.
Hlavní metoda `parse_instructions` využívá dvou pomocných statických metod `_validate_arg` a `_find_num_args`. Jako poslední se provede seřazení instrukcí v dict `_instructions`

Třída `ValidateArguments` slouží jako pomocná třída obsahující metody `is_var`, `is_const` a `escape_string`. Které se používají pro kontroly operandů a jejich obsahu.

Hlavní třída, kterou se spouští samotná interpretace `InterpretWorker(DataStore)`, obsahuje metodu pro spuštění `start_interpreter`, která postupně prochází instrukce z `_instructions`, předpokládá, že instrukce jsou ve správném pořadí. Pro každou instrukci se zavolá metoda `_execute_instructions` kde proěhne kontrola argumentů funkce, pokud je to možné, tak převedení datových typů a zapíše data z argumentů do pomocných proměnných v `DataStore` a `_arg(1-3)_temp_val`. Dále proběhne dynamické zavolání příslušné metody podle názvu instrukce, kde proběhne samotné vykonání instrukce.
Metody `__insert_to_frame` a `__get_var_from_frame` jsou pomocné pro proměnné, první vkládá do příslušného framu a v případě updatování hodnoty kontroluje, zdali proměnná existuje.
Každá z metod vykonávající instrukci používá data z `DataStore`, hlavně zmíněný atribut `_arg(1-3)_temp_val`.

#### Struktura uložených dat
Data uložená ve framech v `DataStore` a  `_arg(1-3)_temp_val` mají následující strukturu datového typu dictionary:   
`'nazev proměnné': {'type': [datovy typ], 'text': [data proměnné]}` jako klíč je použit název proměnné.    
Uložené instrukce jsou taktéž datový typ dictionary, jako klíč je použit `order` z instrukce.   
`'order': {'order': [order], 'opcode': [opcode], 'args': {'arg1': {'type': [datovy typ], 'text': [data proměnné]}}'` případně další argumenty, dle instrukce.

#### Spuštění programu
Program se spouští vstupem do funkce `main`, kde proběhne kontrola vstupních argumentů. Vytvoří se instance třídy `ParseXML` a v případě řádného zadání se zavolá metoda `parse_instructions`. Následuje vytvoření instance třídy `InterpretWorker` a samotné spuštění interpreteru zavoláním metody `start_interpreter`.