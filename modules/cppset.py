from modules import cppvariable as cvar

class CPPSet:
    """
    Represents a C++ set and provides methods to handle set operations.
    """
    def __init__(self, name, py_var_type="auto", elements=None):
        """
        Initialize a CPPSet.

        Parameters:
        ----------
        name : str
            Name of the set.
        py_var_type : str
            Type of elements in the set (e.g., int, float, str).
        elements : list, optional
            Initial elements for the set.
        """
        self.name = name
        self.py_var_type = [py_var_type]
        self.elements = elements or []

    def declaration(self):
        """
        Generate the C++ declaration for the set.

        Returns:
        -------
        str
            The C++ declaration as a string.
        """
        elements_str = ", ".join(map(str, self.elements)) if self.elements else ""
        return f"std::unordered_set<{cvar.CPPVariable.types[self.py_var_type[0]]}> {self.name} = {{ {elements_str} }};"
