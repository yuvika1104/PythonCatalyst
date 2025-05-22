from modules import cppfunction as cfun
from modules import cppvariable as cvar
from modules import cppcodeline as cline
from modules import cppvector as cvec
from modules import cppvector as ctup

class CPPClass:
    """
    Class to represent Python classes as C++ classes.
    """
    
    def __init__(self, name, lineno, end_lineno, bases=None):
        """
        Constructs a CPPClass object.

        Parameters
        ----------
        name : str
            The name of the class.
        lineno : int
            The line where the class is declared in the Python file.
        end_lineno : int
            The line where the class ends in the Python file.
        bases : list of str, optional
            List of base class names (for inheritance).
        """
        self.name = name
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.bases = bases if bases else []  # List of base class names
        self.attributes = {}  # Dictionary of {str: CPPVariable} for class attributes
        self.methods = {}     # Dictionary of {str: CPPFunction} for class methods
        self.vectors = {}     # Dictionary for vector attributes
        self.tuples = {}      # Dictionary for tuple attributes

    def add_attribute(self, variable):
        """
        Adds an attribute (instance variable) to the class.

        Parameters
        ----------
        variable : CPPVariable
            The variable to add as a class attribute.
        """
        self.attributes[variable.name] = variable

    def add_method(self, function):
        """
        Adds a method to the class.

        Parameters
        ----------
        function : CPPFunction
            The function to add as a class method.
        """
        self.methods[function.name] = function

    def get_forward_declaration(self):
        """
        Generates the forward declaration of the class.

        Returns
        -------
        str
            The class's forward declaration.
        """
        declaration = f"class {self.name}"
        # if self.bases:
        #     declaration += " : public " + ", public ".join(self.bases)
        declaration += ";"
        return declaration

    def get_formatted_class_text(self):
        """
        Generates a string with all of the class's C++ code, including attributes and methods.

        Returns
        -------
        str
            String containing the class's C++ code.
        """
        class_text = f"class {self.name}"
        if self.bases:
            class_text += " : public " + ", public ".join(self.bases)
        class_text += "\n{\npublic:\n"

        # Add attributes (instance variables)
        for attr in self.attributes.values():
            attr_type = cvar.CPPVariable.types.get(attr.py_var_type[0], "auto ")
            class_text += f"{cline.CPPCodeLine.tab_delimiter}{attr_type}{attr.name};\n"
        for vector in self.vectors.values():
            vec_decl= vector.declaration()
            class_text+=f"{cline.CPPCodeLine.tab_delimiter}{ vec_decl}\n"
        for tup in self.tuples.values():
            tup_decl= tup.declaration()
            class_text+=f"{cline.CPPCodeLine.tab_delimiter}{ tup_decl}\n"

        # Add methods
        for method in self.methods.values():
            method_text = method.get_formatted_function_text()
            # Indent method text
            method_lines = method_text.split("\n")
            indented_method = "\n".join(
                f"{cline.CPPCodeLine.tab_delimiter}{line}" if line.strip() else line
                for line in method_lines
            )
            class_text += f"{indented_method}\n"

        class_text += "};\n"
        return class_text