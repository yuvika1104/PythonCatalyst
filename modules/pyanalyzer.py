import ast
from modules import cppfile as cfile
from modules import cppfunction as cfun
from modules import cppvariable as cvar
from modules import cppcodeline as cline
from modules import pycatalystexceptions as pcex
from modules import portedfunctions as pf

class PyAnalyzer():
    """
    This is the main class of PyCatalyst that performs the actual analysis and 
    translates python calls to C++ calls
    """
    # Helps evaluate variable types when performing operations on different
    # types
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
    ported_functions = ("print", "sqrt")
    
    
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
        all functions that have been declared in this script

        Parameters
        ----------
        tree : List of ast nodes
            List containing ast nodes from ast.parse
        file_index : int
            Index of the file to write to in the output_files list
        indent : int
            How much indentation a line should have
        """
        # First work through function declarations so we know what calls go to
        # self written functions
        for node in tree:
            if node.__class__ is ast.FunctionDef:
                self.parse_function_header(node,file_index)
        
        # Now we'll parse the bodies of the functions
        for node in tree:
            if node.__class__ is ast.FunctionDef:
                self.analyze_tree(node.body, file_index, node.name, indent)
                
    def parse_function_header(self,node,file_index):
        """
        Parses an ast.FunctionDef node and determines the function name and
        parameters and stores this information in a CPPFunction object which
        is stored in the corresponding CPPFile object

        Parameters
        ----------
        node : ast.FunctionDef
            Node containing the function to parse a header from
        file_index : int
            Index of the file to write to in the output_files list
        """
        func_ref = self.output_files[file_index].functions
        args = node.args
        
        # Verify the function can actually be converted to C++
        if len(args.kw_defaults) > 0 or len(args.kwonlyargs) > 0 \
            or len(args.posonlyargs) > 0 or args.kwarg is not None \
                or args.vararg is not None:
            return
        
        # Default values not directly linked, but they are in order, so we
        # figure out the index offset of when we should begin applying default
        # values to parameters
        default_args_index = len(args.args) - len(args.defaults)
        params = {}
        
        for index in range(len(args.args)):
            name = args.args[index].arg

            # Once index has reached the offset index, we need to start
            # applying default values
            if index >= default_args_index:
                default = args.defaults[index-default_args_index]
                default_type = [type(default.value).__name__]

                # Special handler for strings since their value needs to be
                # wrapped in quotes
                if default_type[0] == "str":
                    params[name] = cvar.CPPVariable(name + "=\"" + default.value + "\"",
                                                    -1, default_type)
                else:
                    params[name] = cvar.CPPVariable(name + "=" + str(default.value),
                                                    -1, default_type)
            else:
                params[name] = cvar.CPPVariable(name, -1, ["auto"])

        func_ref[node.name] = cfun.CPPFunction(node.name, node.lineno,
                                               node.end_lineno, params)
    
    
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
            if node.__class__ is not ast.FunctionDef:
                # Using strategy found in ast.py built-in module
                handler_name = "parse_" + node.__class__.__name__
                # Will find if the function called handler_name exists,
                # otherwise it returns parse_unhandled(fallback function)
                handler = getattr(self, handler_name, self.parse_unhandled)
                handler(node, file_index, function_key, indent)
