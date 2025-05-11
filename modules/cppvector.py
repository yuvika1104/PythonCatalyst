class CPPVector:
    """
    Represents a C++ vector and provides methods to handle vector operations.
    """
    def __init__(self, name, element_type="auto", elements=None):
        """
        Initialize a CPPVector.

        Parameters:
        ----------
        name : str
            Name of the vector.
        element_type : str
            Type of elements in the vector (e.g., int, float).
        elements : list, optional
            Initial elements for the vector.
        """
        self.name = name
        self.element_type = [element_type]
        self.elements = elements or []

    def declaration(self):
        """
        Generate the C++ declaration for the vector.

        Returns:
        -------
        str
            The C++ declaration as a string.
        """
        elements_str = ", ".join(map(str, self.elements))
        return f"std::vector<{self.element_type[0]}> {self.name} = {{ {elements_str} }};"

    def access_element(self, index):
        """
        Generate C++ code to access an element by index.

        Parameters:
        ----------
        index : int or str
            Index of the element.

        Returns:
        -------
        str
            The C++ code for accessing the element.
        """
        return f"{self.name}[{index}]"
