import ast
from modules import cppfile as cfile
from modules import cppfunction as cfun
from modules import cppvariable as cvar
from modules import cppcodeline as cline
from modules import pycatalystexceptions as pcex
from modules import portedfunctions as pf
from modules import cppvector as cvec
from modules import cpptuple as ctup
from modules import cppclass as cclass
from modules import cppset as cset

class PyAnalyzer():
    """
    This is the main class of PyCatalyst that performs the actual analysis and 
    translates python calls to C++ calls
    """
    # Helps evaluate variable types when performing operations on different
    # types (lower value higher precedence)
    type_precedence_dict = {"str": 0, "float": 1, "int": 2, "bool": 3,
                            "auto": 8, "None": 9, "void": 9}
    # Python operators translated to C++ operators
    operator_map = {"Add": "+", "Sub": "-", "Mult": " * ", "Div": "/",
                    "Mod": " % ", "LShift": " << ", "RShift": " >> ",
                    "BitOr": " | ", "BitAnd": " & ", "BitXor": " ^ ",
                    "FloorDiv": "/", "Pow": "Pow", "Not": "!",
                    "Invert": "~", "UAdd": "+", "USub": "-", "And": " && ",
                    "Or": " || "
                    }
    # Tuple of all functions we have a special conversion from python to C++
    ported_functions = ("print", "sqrt", "pow","log","len","append","add", "remove","discard")
    
    
    # Python Comparison operators translated to C++ operators
    # We aren't able to do in/is checks easily, so they are excluded from the
    # mapping
    comparison_map = {"Eq": " == ", "NotEq": " != ", "Lt": " < ",
                      "LtE": " <= ", "Gt": " > ", "GtE": " >= "
                      }
    
    def __init__(self, output_files, raw_lines):
        """
        Initializes an object that will recurse through an AST to convert
        python code text to objects representing C++ code

        Parameters
        ----------
        output_files : list of CPPFile objects
            List to store CPPFiles that the analyzer will reference during
            analysis
        raw_lines : list of str
            List containing the original python script, line by line
        """
        self.output_files = output_files

        self.raw_lines = raw_lines
        
    def analyze(self, tree, file_index, function_key, indent):
        """
        This launches the analysis process, starting with pre-analysis before
        beginning the main analysis step

        Parameters
        ----------
        tree : List of ast nodes
            List containing ast nodes from ast.parse
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        self.pre_analysis(tree, file_index, indent)
        self.analyze_tree(tree, file_index, function_key, indent)
        
        
    def pre_analysis(self, tree, file_index, indent):
        """
        Performs pre-analysis on the script by going through and translating
        all classes and standalone functions declared in this script.
        """
        # First, process all class definitions to register classes and their methods
        for node in tree:
            if node.__class__ is ast.ClassDef:
                self.parse_ClassDef(node, file_index, "-1", indent)

        # Collect class method names to filter them out
        class_method_names = set()
        for cpp_class in self.output_files[file_index].classes.values():
            class_method_names.update(cpp_class.methods.keys())

        # Then, process standalone function declarations (skipping class methods)
        for node in tree:
            if node.__class__ is ast.FunctionDef and node.name not in class_method_names:
                self.parse_function_header(node, file_index)

        # Finally, parse the bodies of standalone functions
        for node in tree:
            if node.__class__ is ast.FunctionDef and node.name not in class_method_names:
                self.analyze_tree(node.body, file_index, node.name, indent)
                
            
    def parse_ClassDef(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.ClassDef node.

        Parameters
        ----------
        node : ast.ClassDef
            The ast.ClassDef node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.
        indent : int
            How much indentation a line should have.
        """
        # Extract base classes
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if len(node.bases) != len(bases):
            self.parse_unhandled(node, file_index, function_key, indent,
                                "TODO: Only simple base classes (by name) are supported")
            return
        
        # Create CPPClass object
        cpp_class = cclass.CPPClass(node.name, node.lineno, node.end_lineno, bases)
        self.output_files[file_index].add_class(cpp_class)

        # Parse class body for methods and attributes
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                # Parse method headers
                self.parse_function_header(item, file_index, class_name=node.name)
            elif isinstance(item, ast.Assign):
                # Handle instance variables (e.g., self.x = 5 in __init__)
                self.parse_class_attribute(item, file_index, node.name, indent)
            else:
                self.parse_unhandled(item, file_index, function_key, indent,
                                    "TODO: Only methods and assignments supported in classes")

        # Parse method bodies
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.analyze_tree(item.body, file_index, f"{node.name}::{item.name}", indent + 1)
                
    def parse_function_header(self, node, file_index, class_name=None):
        """
        Parses an ast.FunctionDef node and determines the function name and
        parameters and stores this information in a CPPFunction object.
        """
        func_ref = self.output_files[file_index].functions
        func_key = f"{class_name}::{node.name}" if class_name else node.name
        # Skip if function is already registered
        if func_key in func_ref:
            print(f"Warning: Skipping duplicate function {func_key}")
            return

        args = node.args
        if len(args.kw_defaults) > 0 or len(args.kwonlyargs) > 0 \
            or len(args.posonlyargs) > 0 or args.kwarg is not None \
                or args.vararg is not None:
            return

        default_args_index = len(args.args) - len(args.defaults)
        params = {}

        for index in range(len(args.args)):
            name = args.args[index].arg
            if index == 0 and name == "self" and class_name:
                continue
            if index >= default_args_index:
                default = args.defaults[index - default_args_index]
                default_type = [type(default.value).__name__]
                if default_type[0] == "str":
                    params[name] = cvar.CPPVariable(name + "=\"" + default.value + "\"",
                                                    -1, default_type)
                else:
                    params[name] = cvar.CPPVariable(name + "=" + str(default.value),
                                                    -1, default_type)
            else:
                params[name] = cvar.CPPVariable(name, -1, ["auto"])

        if node.name =="__init__":
            func = cfun.CPPFunction(class_name, node.lineno, node.end_lineno, params)
            func.return_type[0]="constructor"
        else:
            func = cfun.CPPFunction(node.name, node.lineno, node.end_lineno, params)
        if class_name:
            self.output_files[file_index].classes[class_name].add_method(func)
            func_ref[func_key] = func
        else:
            # print(f"Registering standalone function: {node.name}")
            func_ref[node.name] = func
            
    def parse_class_attribute(self, node, file_index, class_name, indent):
        """
        Parses assignments that define class attributes (e.g., self.x = 5).

        Parameters
        ----------
        node : ast.Assign
            The ast.Assign node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        class_name : str
            Name of the class where the attribute is defined.
        indent : int
            How much indentation a line should have.
        """
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Attribute) \
                or not isinstance(node.targets[0].value, ast.Name) or node.targets[0].value.id != "self":
            self.parse_unhandled(node, file_index, f"{class_name}::__init__", indent,
                                "TODO: Only self.<attribute> assignments are supported in classes")
            return

        attr_name = node.targets[0].attr
        try:
            assign_str, assign_type = self.recurse_operator(node.value, file_index, f"{class_name}::__init__")
        except pcex.TranslationNotSupported as ex:
            self.parse_unhandled(node, file_index, f"{class_name}::__init__", indent, ex.reason)
            return
        # print(assign_str,assign_type)
        class_ref=self.output_files[file_index].classes[class_name]
        code_str=None
        if assign_type[0] == "List":
            self.output_files[file_index].add_include_file("vector")
            vector = cvec.CPPVector(name=attr_name, py_var_type=assign_type[1], elements=assign_str)
            class_ref.vectors[attr_name] = vector
            
            
        elif assign_type[0] == "Tuple":
            self.output_files[file_index].add_include_file("tuple")
            tuple = ctup.CPPTuple(name=attr_name, elements=assign_str, element_types=assign_type[1])
            class_ref.tuples[attr_name] = tuple
            
        elif assign_type[0] =="Set":
            self.output_files[file_index].add_include_file("unordered_set")
            set= cset.CPPSet(name= attr_name,py_var_type=assign_type[1], elements=assign_str)
            class_ref.sets[attr_name]= set
            class_ref.sets[attr_name]= set
            
        else:
        # Create and add attribute to class
            c_var = cvar.CPPVariable(attr_name, node.lineno, assign_type)
            class_ref.add_attribute(c_var)
            code_str = f"this->{attr_name} = {assign_str};"

        # If in __init__, add assignment to the method
        init_key = f"{class_name}::__init__"
        if init_key in self.output_files[file_index].functions and code_str is not None:
            
            self.output_files[file_index].functions[init_key].lines[node.lineno] = \
                cline.CPPCodeLine(node.lineno, node.end_lineno, node.end_col_offset, indent, code_str)
    
    
    def analyze_tree(self, tree, file_index, function_key, indent):
        """
        Accepts an AST node body list and parses through it
        recursively. It will look at each node and call
        the respective functions to handle each type

        Parameters
        ----------
        tree : List of ast nodes
            List containing ast nodes from ast.parse
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        for node in tree:
            # Skipping function definitions as we handled them during
            # pre-analysis
            if node.__class__ not in (ast.FunctionDef, ast.ClassDef):
                # Using strategy found in ast.py built-in module
                handler_name = "parse_" + node.__class__.__name__
                # Will find if the function called handler_name exists,
                # otherwise it returns parse_unhandled(fallback function)
                handler = getattr(self, handler_name, self.parse_unhandled)
                handler(node, file_index, function_key, indent)
    
    
    def parse_unhandled(self, node, file_index, function_key, indent,
                        reason="TODO: Code not directly translatable, manual port required"):
        """
        Handler for any code that cannot be properly translated.
        This will bring the code verbatim from the original python
        script and wrap it in a C++ comment and add the reason it
        wasn't translated one line above it

        Parameters
        ----------
        node : ast node
            The ast node that couldn't be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        reason : str
            The reason why a line of code wasn't translated
        """
        # Get a reference to the correct function to shorten code width
        func_ref = self.output_files[file_index].functions[function_key]
        func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                        node.lineno,
                                                        node.end_col_offset,
                                                        indent,
                                                        "/*" + self.raw_lines[node.lineno-1],
                                                        "", reason)

        # If the code spanned multiple lines, we need to pull all
        # of the lines from the original script, not just the first
        # line
        for index in range(node.lineno+1, node.end_lineno+1):
            func_ref.lines[index] = cline.CPPCodeLine(index,
                                                      index,
                                                      node.end_col_offset,
                                                      indent,
                                                      self.raw_lines[index-1])
        # Add the closing comment symbol on the last line
        func_ref.lines[node.end_lineno].code_str += "*/"

    # Imports
    def parse_Import(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Import node. We don't translate this
        so we just pass on calls to it

        Parameters
        ----------
        node : ast.Import
            The ast.Import node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        pass

    def parse_ImportFrom(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.ImportFrom node. We don't translate this
        so we just pass on calls to it

        Parameters
        ----------
        node : ast.ImportFrom
            The ast.ImportFrom node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        pass          
    
    # Definitions

    # Control Statements
    def parse_If(self, node, file_index, function_key, indent, if_str="if"):
        """
        Handles parsing an ast.If node. Can be called recursively to handle
        nested ifs.

        Parameters
        ----------
        node : ast.If
            The ast.If node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        if_str : str
            Indicates whether to be an if or else if statement
        """
        func_ref= self.output_files[file_index].functions[function_key]
        
        # Parse conditions and add in the code to the current function
        
        try:
            test_str= self.recurse_operator(node.test,file_index,function_key)[0]
            
        except pcex.TranslationNotSupported as ex:
            self.parse_unhandled(node, file_index,function_key,indent, ex.reason)
            return
        
        func_ref.lines[node.lineno]= cline.CPPCodeLine(node.lineno, 
                                                      node.end_lineno, 
                                                      node.end_col_offset,
                                                      indent,
                                                      if_str+" ("+ test_str + ")\n"
                                                      + indent*cline.CPPCodeLine.tab_delimiter
                                                      +"{")
        self.analyze_tree(node.body,file_index, function_key,indent+1)
        
        # Get the last code line and add the closing bracket
        func_ref.lines[node.body[-1].end_lineno].code_str+="\n" + indent*cline.CPPCodeLine.tab_delimiter+ "}"
        
        # Looking for else if or else cases
        if len(node.orelse) == 1 and node.orelse[0].__class__ is ast.If:
            # Else if case
            self.parse_If(node.orelse[0], file_index, function_key, indent,
                          "else if")
        elif len(node.orelse)> 0:
            #Else case
            else_lineno,else_end_col_offset= self.find_else_lineno(node.orelse[0].lineno-2)
            func_ref.lines[else_lineno]= cline.CPPCodeLine(else_lineno,
                                                           else_lineno,
                                                           else_end_col_offset,
                                                           indent,
                                                           "else\n"+ indent*cline.CPPCodeLine.tab_delimiter + "{")
            self.analyze_tree(node.orelse, file_index, function_key, indent+1)
            
            # Get the last code line and add the closing bracket
            func_ref.lines[node.orelse[-1].end_lineno].code_str+= "\n" + indent*cline.CPPCodeLine.tab_delimiter + "}"
    
    
    def find_else_lineno(self, search_index):
        """
        Finds the first else statement starting from the search_index and
        searching upwards in the original python code

        Parameters
        ----------
        search_index : int
            The line number to start searching for the else statement

        Returns
        -------
        search_index : int
            Line number of the else statement
        end_col_offset : int
            Index of the last character of the else in the original python code

        Raises
        ------
        TranslationNotSupported
            If an else is not found
        """        
        while search_index > -1:
            # Check line isn't a comment
            if self.raw_lines[search_index].lstrip()[0] == "#":
                search_index -= 1
                continue
            else:
                end_col_offset = self.raw_lines[search_index].find("else:")
                if end_col_offset < 0:
                    raise pcex.TranslationNotSupported("TODO: No corresponding else found")
                else:
                    end_col_offset += 4
                    
                search_index += 1
                return search_index, end_col_offset

    def parse_While(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.While node. Can be called recursively to handle
        nested whiles.

        Parameters
        ----------
        node : ast.While
            The ast.While node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        func_ref = self.output_files[file_index].functions[function_key]
        
        try:
            test_str = self.recurse_operator(node.test, file_index, function_key)[0]
        except pcex.TranslationNotSupported as ex:
            self.parse_unhandled(node, file_index, function_key, indent, ex.reason)
            return
        
        func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                        node.end_lineno,
                                                        node.end_col_offset,
                                                        indent,
                                                        "while (" + test_str + ")\n"
                                                        + indent * cline.CPPCodeLine.tab_delimiter
                                                        + "{")
        
        self.analyze_tree(node.body, file_index, function_key, indent + 1)
        
        # Closing the body of the while loop
        func_ref.lines[node.body[-1].end_lineno].code_str += "\n" \
                                                             + indent * cline.CPPCodeLine.tab_delimiter \
                                                             + "}"
                                                             
    def parse_Pass(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Pass node. We don't translate this
        so we just pass on calls to it

        Parameters
        ----------
        node : ast.Pass
            The ast.Pass node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        pass        
    
                                               
    def parse_Break(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Break node.

        Parameters
        ----------
        node : ast.Break
            The ast.Break node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        func_ref = self.output_files[file_index].functions[function_key]
        func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                        node.end_lineno,
                                                        node.end_col_offset,
                                                        indent,
                                                        "break;")
        
    def parse_Continue(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Continue node.

        Parameters
        ----------
        node : ast.Continue
            The ast.Continue node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        func_ref = self.output_files[file_index].functions[function_key]
        func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                        node.end_lineno,
                                                        node.end_col_offset,
                                                        indent,
                                                        "continue;")
        
    
    def parse_Return(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Return node.

        Parameters
        ----------
        node : ast.Return
            The ast.Return node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        func_ref = self.output_files[file_index].functions[function_key]
        if node.value is None:
            func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                            node.end_lineno,
                                                            node.end_col_offset,
                                                            indent, "return;")
        else:
            try:
                return_str, return_type = self.recurse_operator(node.value,
                                                                file_index,
                                                                function_key)
            except pcex.TranslationNotSupported as ex:
                self.parse_unhandled(node, file_index, function_key, indent,
                                     ex.reason)
                return

            func_ref.return_type = self.type_precedence(return_type,
                                                        func_ref.return_type)
            func_ref.lines[node.lineno] = cline.CPPCodeLine(node.lineno,
                                                            node.end_lineno,
                                                            node.end_col_offset,
                                                            indent,
                                                            "return " + return_str + ";")
    def convert_docstring(self, doc_string, indent):
        """
        Converts a python docstring to a C++ multiline comment

        Parameters
        ----------
        doc_string : str
            The python docstring
        indent : int
            How much indentation the docstring needs

        Returns
        -------
        str
            The python docstring converted to a C++ multiline comment
        """
        # We remove the preceding whitespace as we will add our own later
        doc_string = doc_string.strip()
        tab_char = cline.CPPCodeLine.tab_delimiter
        return_str = "/*\n"

        # Every line of the docstring will need the indentation added
        while doc_string.find("\n") > -1:
            doc_string = doc_string.lstrip()
            return_str += (tab_char * indent) + doc_string[:doc_string.find("\n")] + "\n"
            doc_string = doc_string[doc_string.find("\n") + 1:]

        # Adds the last piece of the docstring
        doc_string = doc_string.lstrip()
        return_str += tab_char * indent + doc_string
        return return_str + "\n" + (tab_char * indent) + "*/"
    
    
    def parse_Expr(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Expr node.

        Parameters
        ----------
        node : ast.Expr
            The ast.Expr node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        indent : int
            How much indentation a line should have
        """
        func_ref = self.output_files[file_index].functions[function_key]

        # Only worrying about docstrings and function calls
        # Docstrings classified as constants in ast
        if node.value.__class__ is ast.Constant:
            if type(node.value.value) is str:
                # Verify this is a docstring
                start_chars = self.raw_lines[node.value.lineno-1].strip()[0:3]
                if start_chars == '"""' or start_chars == "'''":
                    return_str = self.convert_docstring(node.value.value,
                                                        indent)
                else:
                    self.parse_unhandled(node, file_index, function_key, indent,
                                         "TODO: Constant string not used")
                    return

            else:
                self.parse_unhandled(node, file_index, function_key, indent,
                                     "TODO: Constant not used")
                return

        elif node.value.__class__ is ast.Call:
            try:
                return_str, return_type = self.parse_Call(node.value,
                                                          file_index,
                                                          function_key)

            except pcex.TranslationNotSupported as ex:
                self.parse_unhandled(node, file_index, function_key, indent,
                                     ex.reason)
                return

            return_str += ";"

        else:
            # Any other type doesn't matter as the work it does wouldn't be
            # saved
            self.parse_unhandled(node, file_index, function_key, indent,
                                 "TODO: Value not assigned or used")
            return

        func_ref.lines[node.value.lineno] = cline.CPPCodeLine(node.value.lineno,
                                                              node.value.end_lineno,
                                                              node.end_col_offset,
                                                              indent, return_str)
        
        
    def parse_Assign(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.Assign node.

        Parameters
        ----------
        node : ast.Assign
            The ast.Assign node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.
        indent : int
            How much indentation a line should have.

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated.
        """
        function_ref = self.output_files[file_index].functions[function_key]

        # Won't handle chained assignment
        if len(node.targets) > 1:
            self.parse_unhandled(node, file_index, function_key, indent,
                                 "TODO: Unable to translate chained assignment")
            return

        # Check if this is a class attribute assignment (self.<attr>)
        if isinstance(node.targets[0], ast.Attribute) and \
           isinstance(node.targets[0].value, ast.Name) and \
           node.targets[0].value.id == "self" and \
           "::" in function_key:
            # Extract class name from function_key (e.g., "MyClass::method")
            class_name = function_key.split("::")[0]
            if class_name in self.output_files[file_index].classes:
                self.parse_class_attribute(node, file_index, class_name, indent)
                return
    

        # Handle regular variable assignment
        if not isinstance(node.targets[0], ast.Name):
            self.parse_unhandled(node, file_index, function_key, indent,
                                 "TODO: Only simple variable or self.<attr> assignments supported")
            return

        var_name = node.targets[0].id
        # print(var_name)
        try:
            assign_str, assign_type = self.recurse_operator(node.value,
                                                            file_index,
                                                            function_key)
        except pcex.TranslationNotSupported as ex:
            self.parse_unhandled(node, file_index, function_key, indent,
                                 ex.reason)
            return
        if assign_type[0] == "List":
            self.output_files[file_index].add_include_file("vector")
            vector = cvec.CPPVector(name=var_name, py_var_type=assign_type[1], elements=assign_str)
            function_ref.vectors[var_name] = vector
            code_str = vector.declaration()
            c_code_line = cline.CPPCodeLine(node.lineno, node.end_lineno,
                                            node.end_col_offset, indent,
                                            code_str)
        elif assign_type[0] == "Tuple":
            self.output_files[file_index].add_include_file("tuple")
            tuple = ctup.CPPTuple(name=var_name, elements=assign_str, element_types=assign_type[1])
            function_ref.tuples[var_name] = tuple
            code_str = tuple.declaration()
            c_code_line = cline.CPPCodeLine(node.lineno, node.end_lineno,
                                            node.end_col_offset, indent,
                                            code_str)
        elif assign_type[0] =="Set":
            self.output_files[file_index].add_include_file("unordered_set")
            set= cset.CPPSet(name= var_name,py_var_type=assign_type[1], elements=assign_str)
            function_ref.sets[var_name]= set
            code_str= set.declaration()
            c_code_line = cline.CPPCodeLine(node.lineno, node.end_lineno,
                                            node.end_col_offset, indent,
                                            code_str)
            
        else:
            # Find if name exists in context
            try:
                py_var_type = self.find_var_type(var_name,
                                                 file_index,
                                                 function_key)
                # Verify types aren't changing or we aren't losing precision
                if py_var_type[0] != assign_type[0] \
                   and (py_var_type[0] != "float" or assign_type[0] != "int"):
                    self.parse_unhandled(node, file_index, function_key, indent,
                                         "TODO: Refactor for C++. Variable types "
                                         "cannot change or potential loss of "
                                         "precision occurred")
                    return
                else:
                    code_str = var_name + " = " + str(assign_str) + ";"
                    c_code_line = cline.CPPCodeLine(node.lineno, node.end_lineno,
                                                    node.end_col_offset, indent,
                                                    code_str)
            except pcex.VariableNotFound:
                # Declaration
                c_var = cvar.CPPVariable(var_name, node.lineno, assign_type)
                function_ref.variables[var_name] = c_var
                code_str = var_name + " = " + str(assign_str) + ";"
                c_code_line = cline.CPPCodeLine(node.lineno, node.end_lineno,
                                                node.end_col_offset, indent,
                                                code_str)

        function_ref.lines[node.lineno] = c_code_line
        
    def parse_Call(self, node, file_index, function_key):
        """
        Handles parsing an ast.Call node.

        Parameters
        ----------
        node : ast.Call
            The ast.Call node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.

        Returns
        -------
        return_str : str
            The call represented as a string.
        return_type : list of str
            The return type of the call.

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated.
        """
        func_ref = self.output_files[file_index].functions

        # Process arguments and their types once for all cases
        arg_list = []
        arg_types = []
        for arg in node.args:
            arg_str, arg_type = self.recurse_operator(arg, file_index, function_key)
            arg_list.append(arg_str)
            arg_types.append(arg_type)

        # Handle method calls (e.g., my_list.append(item))
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            var_name = node.func.value.id
            method_name = node.func.attr
            try:
                var_type = self.find_var_type(var_name, file_index, function_key)
                if method_name == "append" :
                # Find the vector in function or class scope
                    vector = func_ref[function_key].vectors.get(var_name)
                    if not vector and '::' in function_key:
                        class_name = function_key.split('::')[0]
                        vector = self.output_files[file_index].classes[class_name].vectors.get(var_name)
                    if not vector:
                        raise pcex.TranslationNotSupported(f"TODO: {var_name} is not a recognized vector")
                
                    # Ensure argument type matches vector's element type
                    if len(arg_types) != 1 or arg_types[0][0] != vector.py_var_type[0]:
                        raise pcex.TranslationNotSupported("TODO: append expects one argument of matching vector element type")
                
                    # self.output_files[file_index].add_include_file("vector")
                    # Delegate to parse_ported_function with vector context
                    return_str,return_type=self.parse_ported_function(file_index, function_key, method_name, arg_list, arg_types)
                    return_str=f"{var_name}.{return_str}"
                    return return_str,return_type
                elif method_name == "add" or method_name=="remove" or method_name=="discard":
                    set = func_ref[function_key].sets.get(var_name)
                    if not set and '::' in function_key:
                        class_name = function_key.split('::')[0]
                        set = self.output_files[file_index].classes[class_name].sets.get(var_name)
                    if not set:
                        raise pcex.TranslationNotSupported(f"TODO: {var_name} is not a recognized set")
                
                    # Ensure argument type matches vector's element type
                    if len(arg_types) != 1 or arg_types[0][0] != set.py_var_type[0]:
                        raise pcex.TranslationNotSupported("TODO: add or remove or discard expects one argument of matching set element type")
                
                    # self.output_files[file_index].add_include_file("unordered_set")
                    # Delegate to parse_ported_function with vector context
                    return_str,return_type=self.parse_ported_function(file_index, function_key, method_name, arg_list, arg_types)
                    return_str=f"{var_name}.{return_str}"
                    return return_str,return_type
                elif method_name =="clear":
                    name = func_ref[function_key].vectors.get(var_name)
                    if not name and '::' in function_key:
                        class_name = function_key.split('::')[0]
                        name = self.output_files[file_index].classes[class_name].vectors.get(var_name)
                    if not name:
                        name = func_ref[function_key].sets.get(var_name)
                    
                    if not name and '::' in function_key:
                        class_name = function_key.split('::')[0]
                        name = self.output_files[file_index].classes[class_name].sets.get(var_name)
                    if not name:
                        raise pcex.TranslationNotSupported(f"TODO: {var_name} is not a recognized collection")
                
                    # Ensure argument type matches vector's element type
                    if len(arg_types) != 0 :
                        raise pcex.TranslationNotSupported("TODO: clear expects no argument ")
            
                    # Delegate to parse_ported_function with vector context
                    return_str,return_type=self.parse_ported_function(file_index, function_key, method_name, arg_list, arg_types)
                    return_str=f"{var_name}.{return_str}"
                    return return_str,return_type
                else:
                    raise pcex.TranslationNotSupported(f"TODO: Method {method_name} on {var_name} not supported")
            except pcex.VariableNotFound:
                raise pcex.TranslationNotSupported(f"TODO: Variable {var_name} not found")

        # Handle regular function calls or casts
        if not isinstance(node.func, ast.Name):
            raise pcex.TranslationNotSupported("TODO: Not a valid call")

        func_name = node.func.id
        if func_name not in cvar.CPPVariable.types and func_name not in func_ref and func_name not in self.ported_functions:
            raise pcex.TranslationNotSupported(f"TODO: Call to function {func_name} not in scope")

        # Handle type casting (e.g., int(), str())
        if func_name in cvar.CPPVariable.types:
            if func_name == "str":
                self.output_files[file_index].add_include_file("string")
                return_str = f"std::to_string({', '.join(arg_list)})"
                return_type = ["str"]
            else:
                return_str = f"({cvar.CPPVariable.types[func_name][:-1]})({', '.join(arg_list)})"
                return_type = [func_name]
        # Handle defined functions
        elif func_name in func_ref:
            function = func_ref[func_name]
            for param, passed_type in zip(function.parameters.values(), arg_types):
                param.py_var_type[0] = self.type_precedence(param.py_var_type, passed_type)[0]
            return_str = f"{func_name}({', '.join(arg_list)})"
            return_type = function.return_type
        # Handle ported functions
        else:
            return self.parse_ported_function(file_index, function_key, func_name, arg_list, arg_types)

        return return_str, return_type
    
    def parse_ported_function(self, file_index, function_key, function, args,
                              arg_types):
        """
        Converts a python version of a function to a C++ version

        Parameters
        ----------
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary
        function : str
            Name of the function to convert
        args : list of str
            List containing the arguments represented as strings
        arg_types : list of list of str
            List containing the types of each argument in a list of str

        Returns
        -------
        return_str : str
            The ported function represented as a string
        return_type : list of str
            The return type of the ported function

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        if function == "print":
            return_str = pf.print_translation(args)
            return_type = ["None"]
            self.output_files[file_index].add_include_file("iostream")

        elif function == "sqrt":
            if len(args) > 1:
                raise pcex.TranslationNotSupported("TODO: Can't square more than 1 item")
            return_str = pf.sqrt_translation(args)
            return_type = ["float"]
            self.output_files[file_index].add_include_file("cmath")
            
        elif function == "pow":
            if len(args) != 2:
                raise pcex.TranslationNotSupported("TODO: Can't find power using less than 2 or more than 2 items")
            return_str = pf.pow_translation(args)
            return_type = ["float"]
            self.output_files[file_index].add_include_file("cmath")
            
        elif function == "log":
            if len(args) > 2:
                raise pcex.TranslationNotSupported("TODO: Can't find log using  more than 2 items")
            return_str = pf.log_translation(args)
            return_type = ["float"]
            self.output_files[file_index].add_include_file("cmath")
            
        elif function == "len":
            if len(args)>1:
                raise pcex.TranslationNotSupported("TODO: Can't find length using  more than 1 item")
            return_str = pf.len_translation(args,arg_types)
            return_type = ["int"]
            
        elif function =="append":
            return_str= pf.append_translation(args,arg_types)
            return_type="void"
            
        elif function =="add":
            return_str= pf.add_translation(args, arg_types)
            return_type="void"
            
        elif function =="remove" or function=="discard":
            return_str= pf.remove_discard_translation(args, arg_types)
            return_type="void"
            
        elif function =="clear":
            return_str= pf.clear_translation()
            return_type="void"


        return return_str, return_type
    
    def parse_Constant(self, node, file_index, function_key):
        """
        Handles parsing an ast.Constant node.

        Parameters
        ----------
        node : ast.Constant
            The ast.Constant node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        return_str : str
            The constant value represented as a string
        return_type : list of str
            The type of the constant
        """
        # Strings need to be wrapped in quotes
        if type(node.value) is str:
            self.output_files[file_index].add_include_file("string")
            return_str = ("\"" + node.value + "\"")
            return_type = ["str"]

        # Python booleans are capital while C++ is lowercase, so we need to
        # translate it
        elif type(node.value) is bool:
            return_str = cvar.CPPVariable.bool_map[str(node.value)]
            return_type = ["bool"]

        else:
            return_str = str(node.value)
            return_type = [type(node.value).__name__]

        return return_str, return_type
    
    
     # Operators
    def parse_BoolOp(self, node, file_index, function_key):
        """
        Handles parsing an ast.BoolOp node.

        Parameters
        ----------
        node : ast.BoolOp
            The ast.BoolOp node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        return_str : str
            The BoolOp represented as a string
        return_type : list of str
            The return type of the BoolOp

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        # List of tuples consisting of (string,[type_string])
        compare_nodes = []
        mixed_types = False
        # Multiple nodes can be chained, so we need to go through all of them
        for internal_node in node.values:
            compare_nodes.append(self.recurse_operator(internal_node,
                                                       file_index,
                                                       function_key))

        # This shouldn't be possible normally, but we check to be safe
        if len(compare_nodes) < 2:
            raise pcex.TranslationNotSupported("TODO: Less than 2 items being compared")

        return_str = ""
        ret_var_type = compare_nodes[0][1][0]
        
        # Go through all but the last one and create a string separated by
        # the C++ version of the python operator
        for compare_node in compare_nodes[:-1]:
            if compare_node[1][0] != ret_var_type:
                mixed_types = True
            return_str += (compare_node[0] +
                           PyAnalyzer.operator_map[node.op.__class__.__name__])

        if compare_nodes[-1][1][0] != ret_var_type:
            mixed_types = True
        return_str += compare_nodes[-1][0]
        
        # Short circuit operators complicate type determination, so if they
        # aren't all the same type, we'll use auto, otherwise these operators
        # keep they type if all items being compared are the same type
        
        if mixed_types:
            return_type = ["auto"]
        else:
            return_type = compare_nodes[0][1]
            
        return_str = "(" + return_str + ")"
        return return_str, return_type  
    
      
    def parse_BinOp(self, node, file_index, function_key):
        """
        Handles parsing an ast.BinOp node.

        Parameters
        ----------
        node : ast.BinOp
            The ast.BinOp node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        return_str : str
            The BinOp represented as a string
        return_type : list of str
            The return type of the BinOp

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        left_str, left_type = self.recurse_operator(node.left,
                                                    file_index,
                                                    function_key)
        right_str, right_type = self.recurse_operator(node.right,
                                                      file_index,
                                                      function_key)

        left_str = str(left_str)
        right_str = str(right_str)
        operator = node.op.__class__.__name__
        if operator in PyAnalyzer.operator_map:
            if operator == "Pow":
                self.output_files[file_index].add_include_file("cmath")
                return_str = "pow(" + left_str + ", " + right_str + ")"
                return_type = ["float"]

            elif operator == "FloorDiv":
                return_str = left_str + " / " + right_str
                # If they aren't both ints, we need to cast to int to truncate
                if left_type[0] != "int" or right_type[0] != "int":
                    return_str = "(int)(" + return_str + ")"
                return_type = ["int"]

            elif operator == "Div":
                return_str = left_str + " / " + right_str
                # We need to cast one to a double or it will perform integer
                # math
                if left_type[0] != "float" or right_type[0] != "float":
                    return_str = "(double)" + return_str
                return_type = ["float"]

            else:
                return_str = left_str \
                              + PyAnalyzer.operator_map[operator] \
                              + right_str

                return_type = self.type_precedence(left_type, right_type)

        return_str = "(" + return_str + ")"
        return return_str, return_type
    
    def type_precedence(self, type_a, type_b):
        """
        We determine which type takes precedent based on loss of
        precision. So a float will take precedence over an int
        If we can't figure it out, we'll default to auto

        Parameters
        ----------
        type_a : list of str
            One of the types to compare
        type_b : list of str
            The other type to compare with

        Returns
        -------
        return_type : list of str
            The list that holds the type that should take precedence
        """
        if type_a[0] in PyAnalyzer.type_precedence_dict and type_b[0] in PyAnalyzer.type_precedence_dict:

            # Smaller value means higher precedence
            if PyAnalyzer.type_precedence_dict[type_a[0]] < PyAnalyzer.type_precedence_dict[type_b[0]]:
                return_type = type_a

            else:
                return_type = type_b

        else:
            # Type doesn't exist in our precedence table
            return_type = ["auto"]

        return return_type
    
    def parse_UnaryOp(self, node, file_index, function_key):
        """
        Handles parsing an ast.UnaryOp node.

        Parameters
        ----------
        node : ast.UnaryOp
            The ast.UnaryOp node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        return_str : str
            The UnaryOp represented as a string
        return_type : list of str
            The return type of the UnaryOp

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        operator = node.op.__class__
        if operator.__name__ not in PyAnalyzer.operator_map:
            raise pcex.TranslationNotSupported("TODO: UnaryOp not supported")

        return_str, return_type = self.recurse_operator(node.operand,
                                                        file_index,
                                                        function_key)

        # Not operation becomes a bool no matter what type it operated on
        if operator is ast.Not:
            return_type = ["bool"]
        else:
            return_type = ["int"]

        return_str = "(" + PyAnalyzer.operator_map[operator.__name__] + return_str + ")"
        return return_str, return_type
    
    
    def parse_Compare(self, node, file_index, function_key):
        """
        Handles parsing an ast.Compare node.

        Parameters
        ----------
        node : ast.Compare
            The ast.Compare node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        return_str : str
            The Compare operation represented as a string
        return_type : list of str
            The return type of the Compare operation

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        # Ensure we can do all types of operations present in code line
        for op in node.ops:
            if op.__class__.__name__ not in PyAnalyzer.comparison_map:
                raise pcex.TranslationNotSupported("TODO: Comparison operation not supported")

        # Comparisons can be chained, so we use the left item as the
        # "last" item to be compared to start the chain
        last_comparator = self.recurse_operator(node.left,
                                                file_index,
                                                function_key)[0]

        return_str = ""
        # Chaining comparisons together with ands
        for index in range(1, len(node.ops)-1):
            comparator = self.recurse_operator(node.comparators[index],
                                               file_index,
                                               function_key)[0]
            return_str += "(" + last_comparator \
                          + PyAnalyzer.comparison_map[node.ops[index-1].__class__.__name__] \
                          + comparator + ") && "
            last_comparator = comparator

        # Add last comparison on the end
        comparator = self.recurse_operator(node.comparators[-1],
                                           file_index,
                                           function_key)[0]

        return_str += "(" + last_comparator + \
                      PyAnalyzer.comparison_map[node.ops[-1].__class__.__name__] \
                      + comparator + ")"

        # All comparisons come back as a bool
        return_type = ["bool"]
        return return_str, return_type
    
    def recurse_operator(self, node, file_index, function_key):
        """
        Accepts a node and determines the appropriate handler function to use
        then passes the parameters to the correct handler function. Called
        recursively to parse through code lines

        Parameters
        ----------
        node : ast node
            The ast node to be translated
        file_index : int
            Index of the file to write to in the output_files list
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        tuple : (str, [str])
            Tuple with the string representation of the operation and the
            return type in a list of a string

        Raises
        ------
        TranslationNotSupported
            If the python code cannot be directly translated
        """
        
        node_type = node.__class__
        if node_type is ast.BinOp:
            return self.parse_BinOp(node, file_index, function_key)

        elif node_type is ast.BoolOp:
            return self.parse_BoolOp(node, file_index, function_key)

        elif node_type is ast.UnaryOp:
            return self.parse_UnaryOp(node, file_index, function_key)

        elif node_type is ast.Compare:
            return self.parse_Compare(node, file_index, function_key)

        elif node_type is ast.Call:
            return self.parse_Call(node, file_index, function_key)

        elif node_type is ast.Name:
            # Variable should already exist if we're using it, so we just grab
            # it from the current context
            try:
                return node.id, self.find_var_type(node.id,
                                                   file_index,
                                                   function_key)
            except pcex.VariableNotFound:
                # Can't handle non declared variables being used
                raise pcex.TranslationNotSupported("TODO: Variable used before declaration")

        elif node_type is ast.Constant:
            return self.parse_Constant(node, file_index, function_key)
        
        elif node_type is ast.List:
            return self.parse_List(node,file_index,function_key)
        elif node_type is ast.Tuple:
            return self.parse_Tuple(node,file_index,function_key)
        elif node_type is ast.Set:
            return self.parse_Set(node,file_index,function_key)
        elif node_type is ast.Subscript:
            try:
                return self.parse_Subscript(node,file_index,function_key)
            except pcex.VariableNotFound:
                raise pcex.TranslationNotSupported("TODO: Variable used before declaration")
        elif node_type is ast.Attribute:
            try:
                return self.parse_Attribute(node, file_index,function_key)
            except pcex.VariableNotFound:
                raise pcex.TranslationNotSupported("TODO:Class Variable used before declaration")
        else:
            # Anything we don't handle
            raise pcex.TranslationNotSupported()
        
        
     # Helper methods
    def find_var_type(self, name, file_index, function_key):
        """
        Finds the type of a variable in a given context

        Parameters
        ----------
        name : str
            Name of the variable to find
        file_index : int
            Index of the file to find the variable
        function_key : str
            Key used to find the correct function in the function dictionary

        Returns
        -------
        list : list of str
            The list reference containing the variable type

        Raises
        ------
        VariableNotFound
            If the variable can't be found in the given context
        """
        if '::' in function_key:
            parts = function_key.split('::')
            if len(parts) != 2:
                raise pcex.TranslationNotSupported("function_key must be in format 'ClassName.method_name'")
    
            class_name = parts[0]
            func_name = parts[1]
            function_ref = self.output_files[file_index].functions[function_key]
            class_ref= self.output_files[file_index].classes[class_name]
            if name in class_ref.attributes:
                return class_ref.attributes[name].py_var_type
            elif name in class_ref.vectors:
                return class_ref.vectors[name].py_var_type
            elif name in class_ref.tuples:
                return ['Tuple']
            elif name in class_ref.sets:
                return['Set']
            
        
            elif name in function_ref.parameters:
                return function_ref.parameters[name].py_var_type

            elif name in function_ref.variables:
                return function_ref.variables[name].py_var_type
            elif name in function_ref.vectors:
                return function_ref.vectors[name].py_var_type
            elif name in function_ref.tuples:
                return ['Tuple']
            elif name in function_ref.sets:
                return['Set']
            else:
                raise pcex.VariableNotFound()
            
        else:
            function_ref = self.output_files[file_index].functions[function_key]
        
            if name in function_ref.parameters:
                return function_ref.parameters[name].py_var_type

            elif name in function_ref.variables:
                return function_ref.variables[name].py_var_type
            elif name in function_ref.vectors:
                return function_ref.vectors[name].py_var_type
            elif name in function_ref.tuples:
                return ['Tuple']
            elif name in function_ref.sets:
                return['Set']

            else:
                raise pcex.VariableNotFound()
    
    def parse_List(self, node, file_index, function_key):
        """
        Handles parsing an ast.List node into a CPPVector.

        Parameters
        ----------
        node : ast.List
            The ast.List node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.
        indent : int
            How much indentation a line should have.
        """
        func_ref = self.output_files[file_index].functions[function_key]

        # Parse elements of the list
        elements = [self.recurse_operator(el, file_index, function_key) for el in node.elts]
         # Extract data types and values
        values = [el[0] for el in elements]
        types = [el[1][0] for el in elements]  

        # Check if all types are the same
        common_type = types[0]
        all_same_type = all(t == common_type for t in types)
        
        if all_same_type:
            py_var_type=common_type
        else:
            raise pcex.TranslationNotSupported("TODO : Hetrogeneous Lists Not Supported")

        
        return values,["List",py_var_type]
    
    
    def parse_Subscript(self, node, file_index, function_key):
        """
        Handles parsing an ast.Subscript node for list indexing.

        Parameters
        ----------
        node : ast.Subscript
            The ast.Subscript node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.
        indent : int
            How much indentation a line should have.
        """
        func_ref = self.output_files[file_index].functions[function_key]
        type="vector"
        name = func_ref.vectors.get(node.value.id)
        if name is None:
            # Check in variables
            name = func_ref.tuples.get(node.value.id)
            type="tuple"
        if name is None:
            # Check in variables
            name = func_ref.variables.get(node.value.id)
            type="variable"
        if name is None:
            # Check in parameters
            name = func_ref.parameters.get(node.value.id)
            type="parameter"
        if name is None:
            # Raise error if not found in any collection
            raise pcex.VariableNotFound()

        index = self.recurse_operator(node.slice, file_index, function_key)[0]
        # print(index)
        if index is None:
            raise pcex.TranslationNotSupported("TODO: Range query on vector")
        if type=="tuple":
            access_code= f"std::get<{index}>({name.name})"
            var_type= name.element_type_list[int(index)]
        else:
        # Generate the C++ code for element access
            access_code = f"{name.name}[{index}]"
            var_type= name.py_var_type
        
        # print(access_code,list_name.element_type)
        return access_code,var_type


    def handle_range_call(self, node, file_index, function_key):
        """
        Extracts the initial limit, final limit, and increment from a range() call.

        Parameters
        ----------
        node : ast.Call
            The ast.Call node representing a range() function.
        file_index : int
            Index of the file in the output_files list.
        function_key : str
            Key to find the correct function in the function dictionary.

        Returns
        -------
        tuple
            (start, end, step) values extracted from the range() call.
        """
        args = []
        for arg in node.args:
            operator_result = self.recurse_operator(arg, file_index, function_key)
            # print(operator_result)
            if operator_result[1][0]!= 'int':
                raise pcex.TranslationNotSupported("Only integer supported")
            args.append(operator_result[0])
    
        # Default values for range
        start, end, step = "0", None, "1"

        # Determine the number of arguments and assign values accordingly
        if len(args) == 1:
            end = args[0]
        elif len(args) == 2:
            start, end = args
        elif len(args) == 3:
            start, end, step = args

        return start, end, step

    def parse_For(self, node, file_index, function_key, indent):
        """
        Handles parsing an ast.For node with numerical range-based loops.

        Parameters
        ----------
        node : ast.For
            The ast.For node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key to find the correct function in the function dictionary.
        indent : int
            How much indentation a line should have.
        """
        func_ref = self.output_files[file_index].functions[function_key]

        try:
            declare=""
        # Ensure iterator is a range() call
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                start, end, step = self.handle_range_call(node.iter, file_index, function_key)
            
                # target_st = node.target.id 
                # if target_st in func_ref.variables:
                #     pass
                # else:
                #     # Register the new variable
                #     declare=indent*cline.CPPCodeLine.tab_delimiter + "int "+target_st+" = 0"
                #     target_var = cvar.CPPVariable(target_st, node.lineno, ['int'])
                #     func_ref.variables[target_var.name] = target_var
                # Convert the target variable
                target_str = self.recurse_operator(node.target, file_index, function_key)[0]
            
                # Construct the C++ for loop header
                loop_header = f"for ({target_str} = {start}; {target_str} < {end}; {target_str} += {step})\n" \
                          + indent * cline.CPPCodeLine.tab_delimiter + "{"
                                                            
            elif isinstance(node.iter, ast.Constant) and isinstance(node.iter.value, int):
                
                end = str(node.iter.value)
                # target_st = node.target.id 
                # if target_st in func_ref.variables:
                #     pass
                # else:
                #     # Register the new variable
                #     target_var = cvar.CPPVariable(target_st, node.lineno, ['int'])
                #     declare=indent*cline.CPPCodeLine.tab_delimiter + "int "+target_st+" = 0"
                #     func_ref.variables[target_var.name] = target_var
                    
                target_str = self.recurse_operator(node.target, file_index, function_key)[0]
                loop_header = f"for ({target_str} = 0; {target_str} < {end}; {target_str}++)\n" \
                          + indent * cline.CPPCodeLine.tab_delimiter + "{"
                          
            else:
                self.parse_unhandled(
                node,
                file_index,
                function_key,
                indent,
                reason="Unsupported iterator type. Only range() and single integers are supported."
                )
                return
            
            func_ref.lines[node.lineno] = cline.CPPCodeLine(
                    node.lineno, node.end_lineno, node.end_col_offset, indent,loop_header
            )

                # Process the body of the for loop
            self.analyze_tree(node.body, file_index, function_key, indent + 1)

                # Closing the body of the for loop
            func_ref.lines[node.body[-1].end_lineno].code_str += "\n" \
                                                                 + indent * cline.CPPCodeLine.tab_delimiter \
                                                            + "}"
        except pcex.TranslationNotSupported as ex:
            self.parse_unhandled(node, file_index, function_key, indent, ex.reason)
            return
        return
    
    def parse_Tuple(self, node, file_index, function_key):
        """
        Handles parsing an ast.Tuple node into a CPPTuple.

        Parameters
        ----------
        node : ast.Tuple
            The ast.Tuple node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.

        Returns
        -------
        tuple
            A tuple containing the values and metadata for the C++ tuple.
        """
        func_ref = self.output_files[file_index].functions[function_key]

        # Parse elements of the tuple
        elements = [self.recurse_operator(el, file_index, function_key) for el in node.elts]
        
        # Extract data types and values
        values = [el[0] for el in elements]
        types = [el[1] for el in elements]
        

        # Return the tuple values and their types
        return values, ["Tuple", types]

    def parse_Attribute(self, node, file_index, function_key):
        """
        Parse an ast.Attribute node (e.g., self.name) and return the transformed attribute name
        and its type. Constructs the function name in the format classname::func_name by
        extracting the class name from function_key using substring operations.
    
        Args:
        node: The ast.Attribute node to parse.
        file_index: The index of the file being processed.
        function_key: Identifier for the current function or method context (e.g., 'ClassName.method_name').
    
        Returns:
        tuple: (transformed_name, var_type, func_name)
               - transformed_name: The attribute name (e.g., 'this->name' for 'self.name').
               - var_type: The type of the attribute.
               - func_name: The function name in the format 'classname::func_name'.
    
        Raises:
        pcex.TranslationNotSupported: If class name cannot be extracted, attribute access is unsupported,
                                      or attribute is undeclared.
        """
        # Extract class name and function name from function_key using substring
        if not isinstance(function_key, str) or '::' not in function_key:
            raise pcex.TranslationNotSupported("Cannot extract class name from function_key: invalid format")
    
        # Split function_key on '.' to get class name and function name
        parts = function_key.split('::')
        if len(parts) != 2:
            raise pcex.TranslationNotSupported("function_key must be in format 'ClassName.method_name'")
    
        class_name = parts[0]
        func_name = parts[1]

        #   Handle attribute access
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            # Convert self.name to this->name
            try:
                var_type = self.find_var_type(node.attr, file_index, function_key)
                return f"this->{node.attr}", var_type
            except pcex.VariableNotFound:
                raise pcex.TranslationNotSupported(f"Class attribute {node.attr} used before declaration")
        else:
            raise pcex.TranslationNotSupported(f"Unsupported attribute access {node.value.id}.{node.attr}")
        
        
        
    def parse_Set(self, node, file_index, function_key):
        """
        Handles parsing an ast.Set node into a CPPSet.

        Parameters
        ----------
        node : ast.Set
            The ast.Set node to be translated.
        file_index : int
            Index of the file to write to in the output_files list.
        function_key : str
            Key used to find the correct function in the function dictionary.

        Returns
        -------
        tuple
            A tuple containing the values and metadata for the C++ set.
        """
        func_ref = self.output_files[file_index].functions[function_key]

        # Parse elements of the set
        elements = [self.recurse_operator(el, file_index, function_key) for el in node.elts]
    
        # Extract data types and values
        values = [el[0] for el in elements]
        types = [el[1][0] for el in elements]

        # Check if all types are the same
        common_type = types[0] if types else "auto"
        all_same_type = all(t == common_type for t in types) if types else True
    
        if not all_same_type:
            raise pcex.TranslationNotSupported("TODO: Heterogeneous sets not supported")
    
        
    
        return values, ["Set", common_type]