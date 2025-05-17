from modules import cppvariable as cvar
class CPPTuple:
    """
    Represents a C++ tuple and provides methods to handle tuple operations.
    """
    def __init__(self, name, elements=None, element_types=None):
        """
        Initialize a CPPTuple.

        Parameters:
        ----------
        name : str
            Name of the tuple.
        elements : list, optional
            Initial elements for the tuple.
        element_types: list, optional
            Initial element types for the tuple.
        """
        self.name = name
        self.elements = elements or []
        self.element_type_list= element_types or []

    def declaration(self):
        """
        Generate the C++ declaration for the tuple.

        Returns:
        -------
        str
            The C++ declaration as a string.
        """
        elements_str = ", ".join(map(str, self.elements))
        return f"std::tuple<{', '.join([cvar.CPPVariable.types[e[0]] for e in self.element_type_list])}> {self.name} = std::make_tuple({elements_str});"

    def access_element(self, index):
        """
        Generate C++ code to access an element by index using std::get.

        Parameters:
        ----------
        index : int
            Index of the element (0-based).

        Returns:
        -------
        str
            The C++ code for accessing the element.
        """
        return f"std::get<{index}>({self.name})"

