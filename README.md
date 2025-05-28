# PyCatalyst: Python-to-C++ Translator

PyCatalyst is a Python-to-C++ translator that converts simple Python scripts into equivalent C++ code. It parses Python code into an Abstract Syntax Tree (AST), analyzes the AST, and generates C++ code with support for variables, functions, classes, lists, tuples, and sets. The project is designed for educational purposes and as a starting point for building more complex transpilers.

## Features

- **Variable Translation**: Maps Python variables to C++ variables with type inference (e.g., `int`, `std::string`).

- **Function Translation**: Converts Python functions to C++ functions, including a `main` function.

- **Class Translation**: Translates Python classes to C++ classes, supporting attributes and methods (limited inheritance).

- Collections

  :

  - Python `list` → C++ `std::vector`
  - Python `tuple` → C++ `std::tuple`
  - Python `set` → C++ `std::unordered_set`

- **Built-in Functions**: Supports common Python built-ins like `print`, `sqrt`, `len`, `append`, `add`, `remove`, `discard`, and `clear`.

- **Comment Preservation**: Converts Python comments to C++ style (`//`).

- **Error Handling**: Raises custom exceptions for unsupported translations or undefined variables.

## Project Structure

The project consists of several Python modules, each handling a specific aspect of the translation process. Below is an overview of the files and their roles:

| File                      | Description                                                  |
| ------------------------- | ------------------------------------------------------------ |
| `cppfile.py`              | Defines `CPPFile` class to represent a C++ file, managing includes, functions, and classes, and generating formatted C++ code. |
| `cppset.py`               | Defines `CPPSet` class to translate Python `set` to C++ `std::unordered_set`. |
| `cpptuple.py`             | Defines `CPPTuple` class to translate Python `tuple` to C++ `std::tuple`. |
| `cppvector.py`            | Defines `CPPVector` class to translate Python `list` to C++ `std::vector`. |
| `cppfunction.py`          | Defines `CPPFunction` class to represent C++ functions, including signatures and code generation. |
| `portedfunctions.py`      | Provides translation functions for Python built-ins (e.g., `print` → `std::cout`, `append` → `push_back`). |
| `cppvariable.py`          | Defines `CPPVariable` class to represent C++ variables with type mapping. |
| `pycatalystexceptions.py` | Defines custom exceptions (`TranslationNotSupported`, `VariableNotFound`) for error handling. |
| `pytranslator.py`         | Defines `PyTranslator` class, the main controller for parsing Python scripts and generating C++ files. |
| `pyanalyzer.py`           | Defines `PyAnalyzer` class to analyze Python AST and convert it to C++ constructs. |
| `cppcodeline.py`          | Defines `CPPCodeLine` class to represent and format a single line of C++ code. |
| `cppclass.py`             | Defines `CPPClass` class to translate Python classes to C++ classes, managing attributes and methods. |

### Module Interactions

- **`PyTranslator`** orchestrates the translation process, reading Python scripts and writing C++ files.
- **`PyAnalyzer`** parses the AST, creating `CPPFunction`, `CPPClass`, `CPPVariable`, `CPPVector`, `CPPTuple`, and `CPPSet` objects.
- **`CPPFile`** aggregates all components (includes, functions, classes) and generates the final C++ code.
- **`portedfunctions.py`** provides translations for Python built-ins, used by `PyAnalyzer`.
- **`CPPCodeLine`** ensures proper indentation and formatting for all generated code.
- Other modules (`CPPSet`, `CPPTuple`, `CPPVector`, `CPPVariable`, `CPPFunction`, `CPPClass`) handle specific Python constructs.

## Installation

### Prerequisites

- Python 3.8 or higher
- No external dependencies required (uses Python’s built-in `ast` module)

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/PyCatalyst.git
   cd PyCatalyst
   ```

2. Place your Python script in the project directory or specify its path when running the translator.

## Usage

1. **Prepare a Python Script**: Create a Python script with supported features (e.g., `example.py`):

   ```python
   class MyClass:
       def __init__(self):
           self.x = 5
           self.my_list = [1, 2, 3]
           self.my_set = {4, 5, 6}
       def my_method(self):
           return self.x
   
   def my_func(x):
       return x + 1
   
   print("Hello, PyCatalyst!")
   ```

2. **Run the Translator**:

   - Create a script (e.g., 

     ```
     run.py
     ```

     ) to invoke 

     ```
     PyTranslator
     ```

     :

     ```python
     from modules.pytranslator import PyTranslator
     
     translator = PyTranslator("example.py", "output")
     translator.run()
     ```

   - Execute:

     ```bash
     python run.py
     ```

   - This generates `main.cpp` in the `output` directory.

3. **Compile and Run the C++ Code**:

   ```bash
   g++ output/main.cpp -o output/main
   ./output/main
   ```

### Example Output

For the above Python script, `main.cpp` will look like:

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_set>

class MyClass;
class MyClass
{
public:
    int x;
    std::vector<int> my_list;
    std::unordered_set<int> my_set;
    MyClass()
    {
        this->x = 5;
        this->my_list = {1, 2, 3};
        this->my_set = {4, 5, 6};
    }
    int my_method()
    {
        return this->x;
    }
};

int my_func(int x)
{
    return x + 1;
}

int main()
{
    std::cout << "Hello, PyCatalyst!" << std::endl;
    return 0;
}
```

## Limitations

- Supported Features

  :

  - Basic variable types (`int`, `float`, `str`, `bool`).
  - Simple functions and class methods.
  - Lists, tuples, sets with homogeneous elements.
  - Basic built-ins (`print`, `sqrt`, `len`, `append`, `add`, `remove`, `discard`, `clear`).

- Unsupported Features

  :

  - Complex types (e.g., dictionaries, nested collections).
  - Advanced Python features (e.g., lambdas, decorators, generators).
  - Heterogeneous collections (e.g., `set([1, "a"])`).
  - Complex inheritance (only simple base class names supported).

- Known Issues

  :

  - Bug in `cppclass.py`: Incorrect import (`cppvector` instead of `cpptuple`) breaks tuple attributes in classes.
  - Limited error messages for unsupported translations.
  - Single-file output (`main.cpp`); no header file support.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.

2. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature
   ```

3. Commit your changes:

   ```bash
   git commit -m "Add your feature"
   ```

4. Push to the branch:

   ```bash
   git push origin feature/your-feature
   ```

5. Open a Pull Request.

### Development Guidelines

- Follow PEP 8 for Python code.
- Add tests for new features (create a `tests` directory if needed).
- Update this README for new features or changes.
- Fix known issues, such as the tuple import bug in `cppclass.py`.

### Suggested Improvements

- Add support for dictionaries (`std::unordered_map`).
- Implement multi-file output (e.g., `.hpp` for classes).
- Enhance error handling with detailed messages.
- Support more Python built-ins (e.g., `range`, `sum`).



